"""
GRF State Archive Module.
Provides high-performance, memory-bounded, chunked and zlib-compressed binary serialization
for Google Research Football (GRF) engine states with random-access seeking,
SHA256 checksum verification, explicit os.fsync flushing, and legacy pickle compatibility.
"""

import os
import io
import sys
import json
import zlib
import pickle
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional, Iterator, Tuple


MAGIC_HEADER = b"FOOTY_GRF_STATE_V1\n"
DEFAULT_CHUNK_SIZE = 50
SIM_STEP_SECONDS = 0.1
SIM_FPS = 10.0


class ReplayIntegrityError(Exception):
    """Raised when replay trajectory and state archive are mismatched, corrupted, or invalid."""
    pass


class GRFStateArchiveWriter:
    """
    Streaming, chunked, compressed writer for GRF engine states.
    Buffers only 1 chunk (e.g. 50 states) in RAM at a time before compressing with zlib
    and appending to disk. Explicitly flushes and executes os.fsync() on close
    to prevent file-lock race conditions and read corruption in WSL/Windows filesystems.
    """

    def __init__(
        self,
        filepath: str,
        match_id: str,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        compression_level: int = 6,
    ):
        self.filepath = str(filepath)
        self.match_id = str(match_id)
        self.chunk_size = max(1, int(chunk_size))
        self.compression_level = compression_level

        self._buffer: List[bytes] = []
        self._total_steps = 0
        self._chunk_offsets: List[Tuple[int, int, int]] = []  # (file_offset, compressed_len, num_states)
        self._sha256 = hashlib.sha256()
        self._is_closed = False

        os.makedirs(os.path.dirname(os.path.abspath(self.filepath)) or '.', exist_ok=True)
        self._file = open(self.filepath, "wb")

        # Reserve space for header by writing initial magic and placeholder
        self._file.write(MAGIC_HEADER)
        self._header_placeholder_pos = self._file.tell()
        # Write 8KB placeholder for JSON header index which will be overwritten on close()
        placeholder = b"\x00" * 8192
        self._file.write(placeholder)
        self._data_start_pos = self._file.tell()

    @property
    def total_steps(self) -> int:
        return self._total_steps

    def append(self, state_bytes: bytes) -> None:
        """Append a single raw GRF state (bytes from env.get_state())."""
        if self._is_closed:
            raise RuntimeError("Cannot append to a closed GRFStateArchiveWriter.")

        self._buffer.append(state_bytes)
        self._sha256.update(state_bytes)
        self._total_steps += 1

        if len(self._buffer) >= self.chunk_size:
            self._flush_chunk()

    def _flush_chunk(self) -> None:
        """Compress and write current buffer chunk to disk."""
        if not self._buffer:
            return

        chunk_data = pickle.dumps(self._buffer, protocol=pickle.HIGHEST_PROTOCOL)
        compressed = zlib.compress(chunk_data, level=self.compression_level)

        offset = self._file.tell()
        comp_len = len(compressed)
        num_states = len(self._buffer)

        self._file.write(compressed)
        self._chunk_offsets.append((offset, comp_len, num_states))
        self._buffer.clear()

    def close(self) -> Dict[str, Any]:
        """
        Flush remaining buffer, write complete header and chunk index,
        and execute explicit .flush() + os.fsync() to guarantee disk persistence in WSL.
        """
        if self._is_closed:
            return {}

        self._flush_chunk()
        data_end_pos = self._file.tell()

        header_dict = {
            "version": 1,
            "match_id": self.match_id,
            "total_steps": self._total_steps,
            "chunk_size": self.chunk_size,
            "compression": "zlib",
            "sim_fps": SIM_FPS,
            "sim_step_seconds": SIM_STEP_SECONDS,
            "state_schema": "grf_chunked_zlib_v1",
            "sha256": self._sha256.hexdigest(),
            "data_start_pos": self._data_start_pos,
            "data_end_pos": data_end_pos,
            "chunk_offsets": self._chunk_offsets,
        }

        header_bytes = json.dumps(header_dict).encode("utf-8")
        if len(header_bytes) > 8192:
            raise ValueError(f"Header index too large ({len(header_bytes)} bytes > 8192)")

        # Pad header to exactly 8192 bytes
        padded_header = header_bytes.ljust(8192, b" ")

        # Write header into reserved placeholder area
        self._file.seek(self._header_placeholder_pos)
        self._file.write(padded_header)

        # Critical WSL I/O Buffer Flushing Protocol:
        # Guarantee buffers are pushed to physical disk before render worker reads.
        self._file.flush()
        try:
            os.fsync(self._file.fileno())
        except (OSError, AttributeError):
            pass

        self._file.close()
        self._is_closed = True
        return header_dict

    def __enter__(self) -> "GRFStateArchiveWriter":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class GRFStateArchiveReader:
    """
    Random-access and streaming reader for chunked compressed GRF state archives.
    Caches the most recently accessed chunk in memory for fast sequential/random seeking.
    Supports legacy pickle archives (.pkl) transparently.
    """

    def __init__(self, filepath: str):
        self.filepath = str(filepath)
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"GRF state archive not found: {self.filepath}")

        self._is_legacy_pickle = False
        self._legacy_states: Optional[List[bytes]] = None
        self._cached_chunk_idx: Optional[int] = None
        self._cached_chunk_states: List[bytes] = []

        with open(self.filepath, "rb") as f:
            magic = f.read(len(MAGIC_HEADER))
            if magic == MAGIC_HEADER:
                header_raw = f.read(8192).decode("utf-8").strip()
                self.header = json.loads(header_raw)
                self.version = self.header.get("version", 1)
                self.match_id = self.header.get("match_id", "")
                self.total_steps = self.header.get("total_steps", 0)
                self.chunk_size = self.header.get("chunk_size", DEFAULT_CHUNK_SIZE)
                self.sha256 = self.header.get("sha256", "")
                self.chunk_offsets = self.header.get("chunk_offsets", [])
            else:
                # Legacy pickle format fallback
                self._is_legacy_pickle = True

        if self._is_legacy_pickle:
            with open(self.filepath, "rb") as f:
                self._legacy_states = pickle.load(f)
            self.total_steps = len(self._legacy_states)
            self.match_id = ""
            self.version = 0
            self.chunk_size = self.total_steps
            self.sha256 = ""
            self.chunk_offsets = []
            self.header = {
                "version": 0,
                "format": "legacy_pickle",
                "total_steps": self.total_steps
            }

    def get_state(self, step: int) -> bytes:
        """Retrieve the raw GRF state bytes at step index (0-indexed) with chunk caching."""
        if step < 0 or step >= self.total_steps:
            raise IndexError(f"Step {step} out of bounds for archive with {self.total_steps} steps.")

        if self._is_legacy_pickle:
            assert self._legacy_states is not None
            return self._legacy_states[step]

        chunk_idx = step // self.chunk_size
        offset_in_chunk = step % self.chunk_size

        if self._cached_chunk_idx != chunk_idx:
            if chunk_idx >= len(self.chunk_offsets):
                raise IndexError(f"Chunk index {chunk_idx} not found in archive index.")
            file_off, comp_len, _ = self.chunk_offsets[chunk_idx]

            with open(self.filepath, "rb") as f:
                f.seek(file_off)
                comp_data = f.read(comp_len)

            decomp_data = zlib.decompress(comp_data)
            self._cached_chunk_states = pickle.loads(decomp_data)
            self._cached_chunk_idx = chunk_idx

        return self._cached_chunk_states[offset_in_chunk]

    def iter_states(self) -> Iterator[bytes]:
        """Iterate sequentially over all states in the archive."""
        if self._is_legacy_pickle:
            assert self._legacy_states is not None
            for s in self._legacy_states:
                yield s
            return

        with open(self.filepath, "rb") as f:
            for chunk_idx, (file_off, comp_len, num_states) in enumerate(self.chunk_offsets):
                f.seek(file_off)
                comp_data = f.read(comp_len)
                decomp_data = zlib.decompress(comp_data)
                states = pickle.loads(decomp_data)
                for s in states:
                    yield s

    def extract_all(self) -> List[bytes]:
        """Extract all states into a single Python list (use when batch processing)."""
        return list(self.iter_states())

    def validate(
        self,
        expected_steps: Optional[int] = None,
        expected_match_id: Optional[str] = None
    ) -> None:
        """Validate archive integrity, step count, match ID, and verify SHA256 checksum."""
        if expected_steps is not None and self.total_steps != expected_steps:
            raise ReplayIntegrityError(
                f"State archive step count mismatch: archive has {self.total_steps} steps, "
                f"expected {expected_steps} steps."
            )

        if expected_match_id and self.match_id and self.match_id != expected_match_id:
            raise ReplayIntegrityError(
                f"State archive match ID mismatch: archive has match_id='{self.match_id}', "
                f"expected '{expected_match_id}'."
            )

        if not self._is_legacy_pickle and self.sha256:
            calc_sha = hashlib.sha256()
            for s in self.iter_states():
                calc_sha.update(s)
            if calc_sha.hexdigest() != self.sha256:
                raise ReplayIntegrityError(
                    f"State archive SHA256 checksum failure: expected {self.sha256}, "
                    f"computed {calc_sha.hexdigest()}."
                )


def load_grf_states(filepath: str, expected_steps: Optional[int] = None) -> List[bytes]:
    """Convenience helper: open archive, validate, and return all states as list."""
    reader = GRFStateArchiveReader(filepath)
    if expected_steps is not None:
        reader.validate(expected_steps=expected_steps)
    return reader.extract_all()
