"""
Central configuration for Footy AI Commentary Pipeline.
"""

from pathlib import Path

# Base directories strictly within backend/commentary
COMMENTARY_DIR = Path(__file__).resolve().parent
BIN_DIR = COMMENTARY_DIR / "bin"
MODELS_DIR = COMMENTARY_DIR / "models"
LLM_MODELS_DIR = MODELS_DIR / "llm"
TTS_MODELS_DIR = MODELS_DIR / "tts"
ARTIFACTS_DIR = COMMENTARY_DIR / "artifacts"
CLIPS_DIR = ARTIFACTS_DIR / "clips"
OUTPUT_DIR = COMMENTARY_DIR / "output"
TTS_VENV_DIR = COMMENTARY_DIR / ".venv-tts"

# Persistent tracking files
VERSIONS_FILE = COMMENTARY_DIR / "versions.json"
CALIBRATION_FILE = COMMENTARY_DIR / "tts_calibration.json"

# Project root paths (read-only references)
FOOTY_ROOT = COMMENTARY_DIR.parent.parent
GOLDEN_VIDEO_PATH = FOOTY_ROOT / "assets/matches/full-match-recordings/burnley-2-4-bournemouth.mp4"
GOLDEN_TIMELINE_PATH = FOOTY_ROOT / "assets/matches/full-match-recordings/burnley-2-4-bournemouth.timeline.json"
GOLDEN_VERIFICATION_PATH = FOOTY_ROOT / "assets/matches/full-match-recordings/burnley-2-4-bournemouth.verification.json"
GOLDEN_TRACE_NPZ_PATH = COMMENTARY_DIR / "tests/fixtures/burnley-bournemouth.npz"
GOLDEN_GOALS_JSON_PATH = FOOTY_ROOT / "backend/verification/season_20261005_234339/reports/recordings/run_1791240220_7b08d5/trace_match_2026_20_3.goals.json"

# Configurable danger weights (can be tuned without altering detector logic)
DANGER_WEIGHTS = {
    "field_progression": 0.25,
    "box_proximity": 0.25,
    "ball_speed": 0.15,
    "defenders_bypassed": 0.15,
    "shot_xg": 0.20,
}

# Pitch dimensions in canonical Footy coordinates
# x in [-1.0, 1.0] (left goal to right goal), y in [-0.42, 0.42] (touchlines)
PITCH_X_MIN = -1.0
PITCH_X_MAX = 1.0
PITCH_Y_MIN = -0.42
PITCH_Y_MAX = 0.42
PENALTY_BOX_X_HOME = -0.80  # left box
PENALTY_BOX_X_AWAY = 0.80   # right box
PENALTY_BOX_Y_HALF_WIDTH = 0.22

# Timing & Speech density bounds
MIN_SPEECH_DENSITY = 0.40
MAX_SPEECH_DENSITY = 0.60
MIN_SILENCE_GAP_SECONDS = 1.5

# Audio processing constants
NATIVE_TTS_SAMPLE_RATE = 24000
MASTER_SAMPLE_RATE = 48000
DUCKING_ATTENUATION_DB = -12.0
DUCKING_ATTACK_SECONDS = 0.15
DUCKING_RELEASE_SECONDS = 0.50

# LLM server parameters
LLM_HOST = "127.0.0.1"
LLM_PORT = 8091
LLM_CONTEXT_SIZE = 8192
LLM_DIRECTOR_TEMPERATURE = 0.25
LLM_WRITER_TEMPERATURE = 0.60

# Model identifiers on Hugging Face
HF_LLM_REPO = "lmstudio-community/Qwen3.5-9B-GGUF"
HF_LLM_FILE = "Qwen3.5-9B-Q4_K_M.gguf"
HF_TTS_REPO = "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"

# Default TTS voice
DEFAULT_VOICE = "Ryan"

# Ensure runtime directories exist
for d in [BIN_DIR, LLM_MODELS_DIR, TTS_MODELS_DIR, ARTIFACTS_DIR, CLIPS_DIR, OUTPUT_DIR]:
    d.mkdir(parents=True, exist_ok=True)
