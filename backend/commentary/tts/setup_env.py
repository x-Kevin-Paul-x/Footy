"""
Phase 13: Setup isolated virtual environment for Qwen3-TTS (.venv-tts).
Installs PyTorch with CUDA 12.8 (including Blackwell), transformers==4.57.3, and qwen-tts.
"""

import sys
import subprocess
from pathlib import Path
from backend.commentary.config import TTS_VENV_DIR


def setup_tts_venv():
    print(f"=== Setting up isolated TTS virtual environment at {TTS_VENV_DIR} ===")
    TTS_VENV_DIR.parent.mkdir(parents=True, exist_ok=True)

    # 1. Create venv if not present
    python_exe = TTS_VENV_DIR / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    if not python_exe.exists():
        print(f"Creating virtual environment: {TTS_VENV_DIR} ...")
        res = subprocess.run([sys.executable, "-m", "venv", str(TTS_VENV_DIR)], check=True)

    pip_exe = TTS_VENV_DIR / ("Scripts/pip.exe" if sys.platform == "win32" else "bin/pip")

    # 2. Upgrade pip
    print("Upgrading pip in .venv-tts...")
    subprocess.run([str(python_exe), "-m", "pip", "install", "--upgrade", "pip"], check=True)

    # 3. CUDA 12.8 is required for this machine's RTX 5070 architecture.
    print("Installing PyTorch (CUDA 12.8) in .venv-tts...")
    cmd_torch = [
        str(pip_exe),
        "install",
        "torch==2.7.1",
        "torchaudio==2.7.1",
        "--index-url",
        "https://download.pytorch.org/whl/cu128",
    ]
    subprocess.run(cmd_torch, check=True)

    # 4. Install qwen-tts and dependencies
    print("Installing qwen-tts and transformers==4.57.3 in .venv-tts...")
    cmd_qwen = [
        str(pip_exe),
        "install",
        "transformers==4.57.3",
        "qwen-tts",
        "soundfile",
        "accelerate",
    ]
    subprocess.run(cmd_qwen, check=True)

    # 5. Verify installation
    verify_cmd = [
        str(python_exe),
        "-c",
        "import torch; import qwen_tts; print('CUDA available:', torch.cuda.is_available(), 'PyTorch version:', torch.__version__)",
    ]
    res = subprocess.run(verify_cmd, capture_output=True, text=True)
    print(f"Verification output:\n{res.stdout.strip()}")
    print("TTS environment ready!")


if __name__ == "__main__":
    setup_tts_venv()
