"""
Robust model downloader for Qwen3.5-9B GGUF and Qwen3-TTS weights.
Downloads directly from Hugging Face into backend/commentary/models/.
"""

import sys
import time
import urllib.request
from pathlib import Path
from typing import List

from backend.commentary.config import (
    LLM_MODELS_DIR,
    TTS_MODELS_DIR,
    HF_LLM_REPO,
    HF_LLM_FILE,
    HF_TTS_REPO,
)


def download_file_with_resume(url: str, dest_path: Path, min_chunk_mb: int = 4):
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = dest_path.with_suffix(dest_path.suffix + ".part")

    initial_size = temp_path.stat().st_size if temp_path.exists() else 0
    headers = {"User-Agent": "FootyCommentary"}
    if initial_size > 0:
        headers["Range"] = f"bytes={initial_size}-"

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            total_size = int(resp.headers.get("content-length", 0)) + initial_size
            mode = "ab" if initial_size > 0 else "wb"
            with open(temp_path, mode) as f:
                downloaded = initial_size
                t0 = time.time()
                while chunk := resp.read(min_chunk_mb * 1024 * 1024):
                    f.write(chunk)
                    downloaded += len(chunk)
                    elapsed = max(0.1, time.time() - t0)
                    speed_mb = (downloaded - initial_size) / (1024 * 1024 * elapsed)
                    if total_size > 0:
                        pct = (downloaded / total_size) * 100
                        print(
                            f"\r{dest_path.name}: {pct:5.1f}% ({downloaded / (1024*1024):.1f}/{total_size / (1024*1024):.1f} MB) at {speed_mb:.1f} MB/s",
                            end="",
                            flush=True,
                        )
                    else:
                        print(f"\r{dest_path.name}: {downloaded / (1024*1024):.1f} MB at {speed_mb:.1f} MB/s", end="", flush=True)

        print()
        temp_path.replace(dest_path)
        return True
    except Exception as e:
        print(f"\nDownload error for {dest_path.name}: {e}")
        return False


def download_qwen_llm():
    print(f"=== Downloading Qwen3.5-9B GGUF ({HF_LLM_FILE}) ===")
    target = LLM_MODELS_DIR / HF_LLM_FILE
    if target.exists() and target.stat().st_size > 1024 * 1024 * 1024:
        print(f"Already exists: {target} ({target.stat().st_size / (1024*1024*1024):.2f} GB)")
        return True

    url = f"https://huggingface.co/{HF_LLM_REPO}/resolve/main/{HF_LLM_FILE}"
    return download_file_with_resume(url, target)


def download_qwen_tts():
    print(f"=== Downloading Qwen3-TTS 1.7B CustomVoice weights ===")
    files = [
        "config.json",
        "generation_config.json",
        "merges.txt",
        "model.safetensors",
        "preprocessor_config.json",
        "tokenizer_config.json",
        "vocab.json",
        "speech_tokenizer/config.json",
        "speech_tokenizer/configuration.json",
        "speech_tokenizer/model.safetensors",
        "speech_tokenizer/preprocessor_config.json",
    ]

    base_url = f"https://huggingface.co/{HF_TTS_REPO}/resolve/main"
    all_ok = True
    for rel_path in files:
        target = TTS_MODELS_DIR / rel_path
        if target.exists() and target.stat().st_size > 0:
            print(f"Exists: {rel_path} ({target.stat().st_size / 1024:.1f} KB)")
            continue

        url = f"{base_url}/{rel_path}"
        ok = download_file_with_resume(url, target)
        if not ok:
            all_ok = False
            break

    return all_ok


if __name__ == "__main__":
    choice = sys.argv[1] if len(sys.argv) > 1 else "all"
    if choice in ("llm", "all"):
        download_qwen_llm()
    if choice in ("tts", "all"):
        download_qwen_tts()
