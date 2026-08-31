---
name: grf-environment-diagnostics
description: >-
  Troubleshooting and health diagnostics for Google Research Football (GRF),
  WSL2 Linux environment, C++ libgame compilation, OpenGL/EGL headless drivers,
  and PyTorch CUDA bindings. Triggers on GRF startup crashes, missing libraries, or WSL IPC timeouts.
---

# Google Research Football (GRF) Environment Diagnostics Guide

This skill provides step-by-step instructions to verify, repair, and optimize the Google Research Football (GRF) and TiKick execution environment.

---

## 1. Quick WSL2 Environment Health Check

Run this diagnostic one-liner from PowerShell to verify that WSL2, Python, PyTorch, and GFootball C++ bindings are properly communicating:

```powershell
wsl python3 -c "import gfootball.env as football_env; import torch; print('CUDA Available:', torch.cuda.is_available()); env = football_env.create_environment(env_name='11_vs_11_stochastic', representation='raw'); obs = env.reset(); print('GRF Engine OK: Obs count =', len(obs)); env.close()"
```

---

## 2. Common Errors and Resolutions

### Error A: `Could not load library libgame.so` or `ImportError: libGL.so.1`
* **Root Cause**: Missing Linux C++ runtime or Mesa graphics dependencies inside WSL2.
* **Resolution** (run inside WSL2):
  ```bash
  sudo apt-get update
  sudo apt-get install -y \
      libsdl2-dev \
      libsdl2-gfx-dev \
      libsdl2-image-dev \
      libsdl2-ttf-dev \
      libboost-all-dev \
      libdirectfb-dev \
      libst-dev \
      mesa-utils \
      xvfb \
      libosmesa6-dev \
      libgl1-mesa-glx \
      libgl1-mesa-dev \
      cmake
  ```

### Error B: `Could NOT find EGL (missing: EGL_INCLUDE_DIR)`
* **Root Cause**: Headless rendering requires EGL development headers.
* **Resolution**:
  ```bash
  sudo apt-get install -y libegl1-mesa-dev
  ```

### Error C: PyTorch CUDA / CUDNN Out of Memory
* When simulating multiple matches concurrently via `grf_batch_runner.py`, use batch inference rather than spawning separate policy models per thread:
  ```python
  # Ensure inference mode and cudnn benchmark are enabled
  torch.backends.cudnn.benchmark = True
  with torch.inference_mode():
      actions, _, rnn_states = policy(obs_batch, rnn_states, masks, avail_actions, deterministic=True)
  ```

---

## 3. Path Translation Protocols (Windows $\leftrightarrow$ WSL2)

* Windows Path: `c:\Users\kevin\OneDrive\Desktop\Projects\Footy\...`
* WSL2 Path: `/mnt/c/Users/kevin/OneDrive/Desktop/Projects/Footy/...`
* Always use helper conversion functions:
  ```python
  def to_wsl_path(win_path: Path) -> str:
      resolved = win_path.resolve()
      drive = resolved.drive.replace(":", "").lower()
      subpath = resolved.as_posix().split(":", 1)[1]
      return f"/mnt/{drive}{subpath}"
  ```
