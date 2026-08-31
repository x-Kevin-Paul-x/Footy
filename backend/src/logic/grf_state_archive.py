"""
GRF State Archive Module.
Provides high-performance, memory-bounded, chunked and zlib-compressed binary serialization
for Google Research Football (GRF) engine states with random-access seeking, per-chunk SHA256
integrity validation, atomic file creation (.tmp -> fsync -> rename), and legacy pickle compatibility.
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


MAGIC_HEADER_V1 = b"FOOTY_GRF_STATE_V1\n"
MAGIC_HEADER_V2 = b"FOOTY_GRF_STATE_V2\n"
DEFAULT_CHUNK_SIZE = 50
SIM_STEP_SECONDS = 0.1
SIM_FPS = 10.0


class ReplayIntegrityError(Exception):
    """Raised when replay trajectory and state archive are mismatched, corrupted, or invalid."""
    pass


class GRFStateArchiveWriter:
    """
    Streaming, chunked, compressed writer for GRF engine states with atomic file creation.
    Buffers only 1 chunk (e.g. 50 states) in RAM at a time before compressing with zlib.
    Calculates per-chunk and whole-archive SHA256 checksums.
    Writes to a .tmp file, executes .flush() + os.fsync(), and atomically renames on close.
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

        self.tmp_filepath = f"{self.filepath}.tmp.{os.getpid()}_{id(self)}"
        self._buffer: List[bytes] = []
        self._total_steps = 0
        self._chunk_offsets: List[Tuple[int, int, int, str]] = []  # (file_offset, comp_len, num_states, chunk_sha256)
        self._global_sha256 = hashlib.sha256()
        self._is_closed = False

        os.makedirs(os.path.dirname(os.path.abspath(self.filepath)) or '.', exist_ok=True)
        self._file = open(self.tmp_filepath, "wb")

        # Reserve space for header by writing V2 magic and 16KB placeholder for metadata
        self._file.write(MAGIC_HEADER_V2)
        self._header_placeholder_pos = self._file.tell()
        placeholder = b"\x00" * 16384
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
        self._global_sha256.update(state_bytes)
        self._total_steps += 1

        if len(self._buffer) >= self.chunk_size:
            self._flush_chunk()

    def _flush_chunk(self) -> None:
        """Compress and write current buffer chunk to disk with per-chunk checksum."""
        if not self._buffer:
            return

        chunk_data = pickle.dumps(self._buffer, protocol=pickle.HIGHEST_PROTOCOL)
        chunk_sha = hashlib.sha256(chunk_data).hexdigest()
        compressed = zlib.compress(chunk_data, level=self.compression_level)

        offset = self._file.tell()
        comp_len = len(compressed)
        num_states = len(self._buffer)

        self._file.write(compressed)
        self._chunk_offsets.append((offset, comp_len, num_states, chunk_sha))
        self._buffer.clear()

    def close(self) -> Dict[str, Any]:
        """
        Flush remaining buffer, write complete header and per-chunk checksum index,
        call .flush() + os.fsync(), and atomically replace target file.
        """
        if self._is_closed:
            return {}

        self._flush_chunk()
        data_end_pos = self._file.tell()

        header_dict = {
            "version": 2,
            "match_id": self.match_id,
            "total_steps": self._total_steps,
            "chunk_size": self.chunk_size,
            "compression": "zlib",
            "sim_fps": SIM_FPS,
            "sim_step_seconds": SIM_STEP_SECONDS,
            "state_schema": "grf_chunked_zlib_v2",
            "sha256": self._global_sha256.hexdigest(),
            "data_start_pos": self._data_start_pos,
            "data_end_pos": data_end_pos,
            "chunk_offsets": self._chunk_offsets,
        }

        header_bytes = json.dumps(header_dict).encode("utf-8")
        if len(header_bytes) > 16384:
            raise ValueError(f"Header index too large ({len(header_bytes)} bytes > 16384)")

        # Pad header to exactly 16384 bytes
        padded_header = header_bytes.ljust(16384, b" ")

        # Write header into reserved placeholder area
        self._file.seek(self._header_placeholder_pos)
        self._file.write(padded_header)

        # Critical WSL I/O Buffer Flushing Protocol
        self._file.flush()
        try:
            os.fsync(self._file.fileno())
        except (OSError, AttributeError):
            pass

        self._file.close()
        self._is_closed = True

        # Atomic file rename to guarantee file is complete before any reader accesses it
        os.replace(self.tmp_filepath, self.filepath)
        return header_dict

    def __enter__(self) -> "GRFStateArchiveWriter":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # Exception occurred during simulation: clean up tmp file
            if not self._is_closed:
                try:
                    self._file.close()
                except Exception:
                    pass
                self._is_closed = True
                if os.path.exists(self.tmp_filepath):
                    try:
                        os.remove(self.tmp_filepath)
                    except Exception:
                        pass
        else:
            self.close()


class GRFStateArchiveReader:
    """
    Random-access and streaming reader for chunked compressed GRF state archives.
    Caches the most recently accessed chunk in memory for fast sequential/random seeking.
    Validates per-chunk SHA256 checksums automatically during decompression.
    Supports legacy pickle archives (.pkl) and V1/V2 .grfstate formats transparently.
    """

    def __init__(self, filepath: str):
        self.filepath = str(filepath)
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"GRF state archive not found: {self.filepath}")

        self._is_legacy_pickle = False
        self._legacy_states: Optional[List[bytes]] = None
        self._cached_chunk_idx: Optional[int] = None
        self._cached_chunk_states: List[bytes] = []
        self._file = open(self.filepath, "rb")

        magic_candidate = self._file.read(len(MAGIC_HEADER_V2))
        if magic_candidate == MAGIC_HEADER_V2:
            header_raw = self._file.read(16384).decode("utf-8").strip()
            self.header = json.loads(header_raw)
            self.version = 2
        elif magic_candidate == MAGIC_HEADER_V1:
            header_raw = self._file.read(8192).decode("utf-8").strip()
            self.header = json.loads(header_raw)
            self.version = 1
        else:
            # Legacy pickle format fallback
            self._is_legacy_pickle = True

        if not self._is_legacy_pickle:
            self.match_id = self.header.get("match_id", "")
            self.total_steps = self.header.get("total_steps", 0)
            self.chunk_size = self.header.get("chunk_size", DEFAULT_CHUNK_SIZE)
            self.sha256 = self.header.get("sha256", "")
            self.chunk_offsets = self.header.get("chunk_offsets", [])
        else:
            self._file.seek(0)
            self._legacy_states = pickle.load(self._file)
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

    def close(self) -> None:
        """Close internal open file handle."""
        if hasattr(self, "_file") and self._file is not None and not self._file.closed:
            self._file.close()

    def __enter__(self) -> "GRFStateArchiveReader":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        self.close()

    def get_state(self, step: int) -> bytes:
        """Retrieve the raw GRF state bytes at step index (0-indexed) with chunk caching and validation."""
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
            
            chunk_entry = self.chunk_offsets[chunk_idx]
            file_off = chunk_entry[0]
            comp_len = chunk_entry[1]
            chunk_sha = chunk_entry[3] if len(chunk_entry) > 3 else None

            self._file.seek(file_off)
            comp_data = self._file.read(comp_len)
            decomp_data = zlib.decompress(comp_data)

            # Per-chunk integrity verification
            if chunk_sha:
                calc_sha = hashlib.sha256(decomp_data).hexdigest()
                if calc_sha != chunk_sha:
                    raise ReplayIntegrityError(
                        f"Chunk {chunk_idx} SHA256 checksum mismatch (expected {chunk_sha}, computed {calc_sha})"
                    )

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

        for chunk_idx, chunk_entry in enumerate(self.chunk_offsets):
            file_off = chunk_entry[0]
            comp_len = chunk_entry[1]
            chunk_sha = chunk_entry[3] if len(chunk_entry) > 3 else None

            self._file.seek(file_off)
            comp_data = self._file.read(comp_len)
            decomp_data = zlib.decompress(comp_data)

            if chunk_sha:
                calc_sha = hashlib.sha256(decomp_data).hexdigest()
                if calc_sha != chunk_sha:
                    raise ReplayIntegrityError(f"Chunk {chunk_idx} SHA256 checksum mismatch")

            states = pickle.loads(decomp_data)
            for s in states:
                yield s

    def extract_all(self) -> List[bytes]:
        """Extract all states into a single Python list."""
        return list(self.iter_states())

    def validate(
        self,
        expected_steps: Optional[int] = None,
        expected_match_id: Optional[str] = None
    ) -> None:
        """Validate archive integrity, step count, match ID, schema version, and SHA256 checksum."""
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

        # Schema version validation: V2 archives must declare grf_chunked_zlib_v2.
        # Reject stale V1 schema strings in V2 files to prevent cross-version replay corruption.
        if not self._is_legacy_pickle:
            schema = self.header.get("state_schema", "")
            if schema and schema != "grf_chunked_zlib_v2":
                raise ReplayIntegrityError(
                    f"State archive schema version mismatch: found '{schema}', "
                    f"expected 'grf_chunked_zlib_v2'. Archive may be from an incompatible version."
                )

        if not self._is_legacy_pickle and self.sha256:
            calc_sha = hashlib.sha256()
            for s in self.iter_states():
                calc_sha.update(s)
            if calc_sha.hexdigest() != self.sha256:
                raise ReplayIntegrityError(
                    f"State archive global SHA256 checksum failure: expected {self.sha256}, "
                    f"computed {calc_sha.hexdigest()}."
                )


def load_grf_states(filepath: str, expected_steps: Optional[int] = None) -> List[bytes]:
    """Convenience helper: open archive, validate, and return all states as list."""
    reader = GRFStateArchiveReader(filepath)
    if expected_steps is not None:
        reader.validate(expected_steps=expected_steps)
    return reader.extract_all()
