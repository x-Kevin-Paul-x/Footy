const { spawn } = require('node:child_process');
const { resolve } = require('node:path');
const { existsSync } = require('node:fs');
const root = resolve(__dirname, '..');
const python = process.env.FOOTY_PYTHON || resolve(root, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
if (!existsSync(python)) {
  console.error('Create .venv and install the project before starting the backend.');
  process.exit(1);
}
const child = spawn(python, ['-m', 'uvicorn', 'api_fastapi:app', '--reload', '--reload-dir', 'backend/src', '--port', process.env.FOOTY_API_PORT || '5001'], { cwd: root, stdio: 'inherit' });
for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => child.kill(signal));
child.on('error', error => { console.error(error.message); process.exit(1); });
child.on('exit', code => process.exit(code || 0));
