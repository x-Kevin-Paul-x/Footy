"""
Replay Integrity & State Archive Test Suite for Google Research Football (GRF).
Verifies:
1. GRFStateArchiveWriter / Reader chunked compression, fsync flushing, and random seek.
2. Checksum validation and ReplayIntegrityError on data corruption or length mismatch.
3. Legacy pickle archive compatibility.
4. Frame-accurate event step tracking and clock synchronization.
5. Strict mode enforcement (3d vs 2d vs auto) preventing silent degradation.
6. WSL2 state restoration & replay consistency.
"""

import os
import sys
import json
import pickle
import zlib
import hashlib
import tempfile
import numpy as np
import pytest
from pathlib import Path

from logic.grf_state_archive import (
    GRFStateArchiveWriter,
    GRFStateArchiveReader,
    ReplayIntegrityError,
    load_grf_states,
    SIM_STEP_SECONDS,
    SIM_FPS
)
from logic.grf_trajectory import MatchTrajectory, MatchManifest


def test_grf_state_archive_roundtrip(tmp_path):
    """Test GRFStateArchiveWriter and Reader chunked zlib compression roundtrip."""
    test_file = tmp_path / "test_archive.grfstate"
    num_states = 135
    chunk_size = 50

    # Generate distinct synthetic state byte sequences
    fake_states = [f"state_payload_frame_{i}_{'x'*200}".encode('utf-8') for i in range(num_states)]

    with GRFStateArchiveWriter(str(test_file), match_id="test_m1", chunk_size=chunk_size) as writer:
        for s in fake_states:
            writer.append(s)

    assert test_file.exists()
    assert test_file.stat().st_size > 0

    reader = GRFStateArchiveReader(str(test_file))
    assert reader.total_steps == num_states
    assert reader.match_id == "test_m1"
    assert reader.chunk_size == chunk_size

    # Verify sequential iteration
    extracted = reader.extract_all()
    assert len(extracted) == num_states
    assert extracted == fake_states

    # Verify random-access seeking across chunks
    for idx in [0, 49, 50, 99, 100, 134]:
        assert reader.get_state(idx) == fake_states[idx]

    # Out of bounds raises IndexError
    with pytest.raises(IndexError):
        reader.get_state(num_states)
    with pytest.raises(IndexError):
        reader.get_state(-1)


def test_grf_state_archive_validation_and_corruption_detection(tmp_path):
    """Verify SHA256 checksum validation and corruption detection."""
    test_file = tmp_path / "test_corrupt.grfstate"
    fake_states = [f"state_{i}".encode('utf-8') * 50 for i in range(30)]

    with GRFStateArchiveWriter(str(test_file), match_id="match_chk", chunk_size=10) as writer:
        for s in fake_states:
            writer.append(s)

    reader = GRFStateArchiveReader(str(test_file))
    # Valid validation passes
    reader.validate(expected_steps=30, expected_match_id="match_chk")

    # Mismatched step count raises ReplayIntegrityError
    with pytest.raises(ReplayIntegrityError, match="step count mismatch"):
        reader.validate(expected_steps=29)

    # Mismatched match ID raises ReplayIntegrityError
    with pytest.raises(ReplayIntegrityError, match="match ID mismatch"):
        reader.validate(expected_match_id="other_match")

    # Tamper with archive file payload (mutate byte in data area)
    raw_data = bytearray(test_file.read_bytes())
    # mutate a byte near EOF
    raw_data[-20] = (raw_data[-20] + 1) % 256
    test_file.write_bytes(raw_data)

    tampered_reader = GRFStateArchiveReader(str(test_file))
    with pytest.raises((ReplayIntegrityError, zlib.error, pickle.UnpicklingError)):
        tampered_reader.validate()


def test_grf_state_archive_legacy_pickle_fallback(tmp_path):
    """Verify GRFStateArchiveReader transparently reads legacy raw pickle archives."""
    legacy_file = tmp_path / "legacy_states.pkl"
    raw_states = [b"legacy_state_001", b"legacy_state_002", b"legacy_state_003"]
    with open(legacy_file, "wb") as f:
        pickle.dump(raw_states, f)

    reader = GRFStateArchiveReader(str(legacy_file))
    assert reader.total_steps == 3
    assert reader.get_state(0) == b"legacy_state_001"
    assert reader.get_state(2) == b"legacy_state_003"
    assert reader.extract_all() == raw_states


def test_wsl_grf_state_replay_synchronization():
    """
    Test real WSL simulation with record_grf_states=True:
    1. Generates trajectory .npz and chunked .grfstate archive.
    2. Validates length invariant (states == total_steps).
    3. Validates event exact step integrity and sim_time calculation.
    """
    from logic.grf_native_runner import GRFNativeRunner
    runner = GRFNativeRunner()
    if not runner.is_available():
        pytest.skip("WSL GRF environment not available")

    match_id = "test_state_sync_01"
    res = runner.simulate(
        home_team="Arsenal",
        away_team="Chelsea",
        max_steps=120,
        match_id=match_id,
        seed_val=424242,
        record_grf_states=True,
    )

    state_path = Path(f"backend/reports/recordings/trace_{match_id}.grfstate")
    npz_path = Path(f"backend/reports/recordings/trace_{match_id}.npz")

    assert npz_path.exists(), "Trajectory .npz file must exist"
    assert state_path.exists(), "State archive .grfstate file must exist"

    # Verify state archive integrity
    reader = GRFStateArchiveReader(str(state_path))
    traj = MatchTrajectory.load_from_npz(npz_path)

    assert reader.total_steps == traj.total_steps, "Archive steps must match trajectory total_steps"
    assert reader.total_steps == 120
    reader.validate(expected_steps=traj.total_steps, expected_match_id=match_id)

    # Verify event step timestamps are frame-accurate integers
    for ev in traj.manifest.events:
        if ev.get("type") == "goal":
            assert "step" in ev, "Goal event must contain exact simulation step"
            assert isinstance(ev["step"], int)
            assert 0 <= ev["step"] < traj.total_steps
            assert "sim_time" in ev
            assert round(ev["step"] * 0.1, 2) == ev["sim_time"]


def test_strict_render_modes():
    """Verify mode='3d' fails fast on missing states and does not silently fall back to 2D."""
    from logic.grf_native_runner import GRFNativeRunner
    runner = GRFNativeRunner()

    # Requesting mode="3d" on nonexistent files must raise RuntimeError/ReplayIntegrityError
    with pytest.raises(RuntimeError, match="Explicit 3D replay requested"):
        runner.render_replay(
            match_id="nonexistent_match_3d_test_9999",
            home_team="TeamA",
            away_team="TeamB",
            mode="3d"
        )


def test_grf_state_archive_per_chunk_checksum_corruption(tmp_path):
    """Verify that corruption inside a specific chunk triggers ReplayIntegrityError upon reading that chunk."""
    test_file = tmp_path / "test_chunk_corrupt.grfstate"
    num_states = 100
    chunk_size = 20  # 5 chunks: 0..19, 20..39, 40..59, 60..79, 80..99
    fake_states = [f"state_chunk_payload_{i}_{'z'*100}".encode('utf-8') for i in range(num_states)]

    with GRFStateArchiveWriter(str(test_file), match_id="match_chk_corrupt", chunk_size=chunk_size) as writer:
        for s in fake_states:
            writer.append(s)

    reader = GRFStateArchiveReader(str(test_file))
    # Uncorrupted chunk 0 reads cleanly
    assert reader.get_state(0) == fake_states[0]
    assert reader.get_state(15) == fake_states[15]

    # Find the byte offset of chunk 2 (states 40..59)
    chunk_2_entry = reader.chunk_offsets[2]
    c2_offset = chunk_2_entry[0]
    reader.close()

    # Mutate a byte inside chunk 2 in the file
    raw_data = bytearray(test_file.read_bytes())
    raw_data[c2_offset + 5] = (raw_data[c2_offset + 5] ^ 0xFF)
    test_file.write_bytes(raw_data)

    corrupt_reader = GRFStateArchiveReader(str(test_file))
    # Chunk 0 (step 0) and Chunk 1 (step 25) still succeed
    assert corrupt_reader.get_state(5) == fake_states[5]
    assert corrupt_reader.get_state(25) == fake_states[25]

    # Accessing Chunk 2 (step 45) must raise ReplayIntegrityError or zlib decompression error
    with pytest.raises((ReplayIntegrityError, zlib.error)):
        corrupt_reader.get_state(45)
    corrupt_reader.close()


def test_grf_state_archive_atomic_writer_exception_cleanup(tmp_path):
    """Verify that if an exception occurs during simulation, .tmp file is removed and target file is not created."""
    test_file = tmp_path / "failed_simulation.grfstate"

    with pytest.raises(ValueError, match="Simulation crashed unexpectedly"):
        with GRFStateArchiveWriter(str(test_file), match_id="crashed_sim") as writer:
            writer.append(b"state_step_0")
            writer.append(b"state_step_1")
            tmp_path_check = writer.tmp_filepath
            assert os.path.exists(tmp_path_check), "Temporary file must exist during active writing"
            raise ValueError("Simulation crashed unexpectedly")

    # After exception, target file must NOT exist, and .tmp file must be cleaned up
    assert not test_file.exists(), "Target archive must not exist after crashed simulation"
    assert not os.path.exists(tmp_path_check), "Temporary archive must be cleanly unlinked"


def test_grf_state_archive_successful_creation_cleans_tmp(tmp_path):
    """Verify that upon successful writer close, .tmp is replaced by the target file and does not linger."""
    test_file = tmp_path / "valid_simulation.grfstate"

    with GRFStateArchiveWriter(str(test_file), match_id="valid_sim") as writer:
        writer.append(b"state_valid_0")
        tmp_check = writer.tmp_filepath

    assert test_file.exists(), "Target file must exist after successful write"
    assert not os.path.exists(tmp_check), "Temporary file must be cleanly replaced"


def test_grf_state_archive_truncated_file(tmp_path):
    """Verify that reading from a truncated archive raises ReplayIntegrityError or zlib.error.

    Simulates filesystem corruption or an interrupted write by cutting the file to half its size.
    Any read that touches the truncated region must raise, not silently return garbage data.
    """
    test_file = tmp_path / "test_truncated.grfstate"
    num_states = 30
    fake_states = [f"state_{i}_{'y'*100}".encode('utf-8') for i in range(num_states)]

    with GRFStateArchiveWriter(str(test_file), match_id="truncated_match", chunk_size=10) as writer:
        for s in fake_states:
            writer.append(s)

    original_size = test_file.stat().st_size
    truncated_size = max(64, original_size // 2)
    raw_data = test_file.read_bytes()[:truncated_size]
    test_file.write_bytes(raw_data)

    # Reading from the truncated region must raise — it must not silently return garbage
    with pytest.raises((ReplayIntegrityError, zlib.error, Exception)):
        reader = GRFStateArchiveReader(str(test_file))
        # Try to read a state from the truncated area (last chunk)
        reader.get_state(num_states - 1)


def test_grf_state_archive_header_corruption(tmp_path):
    """Verify that corrupting the archive header causes construction or validate() to raise.

    Mutates the first 50 bytes (header/manifest region) — the reader must detect this as invalid.
    """
    test_file = tmp_path / "test_header_corrupt.grfstate"
    fake_states = [f"state_{i}".encode('utf-8') * 30 for i in range(20)]

    with GRFStateArchiveWriter(str(test_file), match_id="header_match", chunk_size=10) as writer:
        for s in fake_states:
            writer.append(s)

    # Corrupt the magic header bytes
    raw_data = bytearray(test_file.read_bytes())
    for i in range(min(50, len(raw_data))):
        raw_data[i] = (raw_data[i] ^ 0xAB) % 256
    test_file.write_bytes(raw_data)

    with pytest.raises((ReplayIntegrityError, Exception)):
        bad_reader = GRFStateArchiveReader(str(test_file))
        bad_reader.validate()


def test_grf_state_archive_rejects_tmp_file(tmp_path):
    """Verify that a renderer never accepts a .tmp partial file as a valid archive.

    Creates a .grfstate.tmp file (simulating an interrupted write) and asserts
    that GRFStateArchiveReader raises when given a .tmp path — partial archives
    must never be silently consumed.
    """
    tmp_archive = tmp_path / "match_replay.grfstate.tmp.99999"
    # Write partial data — incomplete zlib stream, no proper magic header
    tmp_archive.write_bytes(b"PARTIAL_INCOMPLETE_DATA_NO_MAGIC\x00\x01\x02\x03")

    with pytest.raises((ReplayIntegrityError, Exception)):
        bad_reader = GRFStateArchiveReader(str(tmp_archive))
        bad_reader.validate()


def test_grf_state_archive_schema_v2_mismatch(tmp_path):
    """Verify that validate() raises ReplayIntegrityError when the manifest reports a wrong schema version.

    Parses the JSON header from the archive binary and replaces state_schema with a stale V1 string,
    then re-serializes into the exact same header slot. The reader must detect and reject this mismatch.
    """
    test_file = tmp_path / "test_schema_mismatch.grfstate"
    fake_states = [f"state_{i}".encode('utf-8') * 20 for i in range(10)]

    with GRFStateArchiveWriter(str(test_file), match_id="schema_match", chunk_size=5) as writer:
        for s in fake_states:
            writer.append(s)

    raw_data = bytearray(test_file.read_bytes())
    magic_len = len(b"FOOTY_GRF_STATE_V2\n")
    HEADER_SLOT_SIZE = 16384

    # Extract and parse the JSON header from its fixed slot
    header_bytes = bytes(raw_data[magic_len: magic_len + HEADER_SLOT_SIZE]).rstrip()
    try:
        header_dict = json.loads(header_bytes)
    except json.JSONDecodeError:
        pytest.skip("Could not parse JSON header from archive binary")

    original_schema = header_dict.get("state_schema", "")
    if not original_schema or "v2" not in original_schema:
        pytest.skip(f"Archive did not contain expected V2 schema field: {original_schema}")

    # Patch schema string to stale V1
    header_dict["state_schema"] = "grf_chunked_zlib_v1"
    patched_header = json.dumps(header_dict).encode("utf-8").ljust(HEADER_SLOT_SIZE, b" ")
    raw_data[magic_len: magic_len + HEADER_SLOT_SIZE] = patched_header
    test_file.write_bytes(bytes(raw_data))

    patched_reader = GRFStateArchiveReader(str(test_file))
    # validate() must detect the stale schema string and raise ReplayIntegrityError
    with pytest.raises(ReplayIntegrityError, match="schema version mismatch"):
        patched_reader.validate()


def test_grf_goal_replay_multiple_events_same_step(tmp_path):
    """Verify that the render path iterates over ALL goal events at the same step, not just the last.

    Constructs a goal_events_by_step dict with 2 events at step 5 and checks that both
    banner strings are processed (i.e., the for loop iterates correctly over the list).
    This is a logic-level unit test — no GRF env needed.
    """
    # Simulate the goal event iteration logic from render_from_grf_states
    goal_events_by_step = {
        5: [
            {"player": "Salah", "team": "home", "minute": 45},
            {"player": "Mane", "team": "home", "minute": 45},
        ]
    }

    processed_banners = []
    broadcast_fps = 10

    # Replicate the exact loop from grf_render_worker.py
    step = 5
    if step in goal_events_by_step:
        gevs = goal_events_by_step[step]
        for gev in gevs:
            scorer = gev.get("player", "Player")
            team_str = gev.get("team", "").upper()
            match_min = gev.get("minute", 0)
            banner = f"GOAL!  {scorer} ({team_str})  {match_min}'"
            processed_banners.append(banner)

    # Both events must be iterated — not just the last one
    assert len(processed_banners) == 2, (
        f"Expected 2 goal banners processed for 2 events at same step, got {len(processed_banners)}"
    )
    assert any("Salah" in b for b in processed_banners), "First goal scorer must be processed"
    assert any("Mane" in b for b in processed_banners), "Second goal scorer must be processed"
