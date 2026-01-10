const { spawn } = require('child_process');
const fs = require('fs');
const http = require('http');
const path = require('path');

const rootDir = path.resolve(__dirname, '..');
const backendDir = path.join(rootDir, 'backend');
const frontendDir = path.join(rootDir, 'frontend');

const pythonPath = process.env.E2E_PYTHON || path.join(backendDir, '.venv311', 'bin', 'python');
const pythonBin = fs.existsSync(pythonPath) ? pythonPath : 'python3';

const backendEnv = {
  ...process.env,
  DATABASE_URL: process.env.DATABASE_URL || 'sqlite:///./data/e2e.db',
  CORS_ORIGINS: process.env.CORS_ORIGINS || 'http://localhost:3000,http://localhost:3001,http://localhost:5173,http://127.0.0.1:5173',
  PYTHONUNBUFFERED: '1',
};

const frontendEnv = {
  ...process.env,
  VITE_API_URL: process.env.VITE_API_URL || 'http://127.0.0.1:8000',
};

const backend = spawn(
  pythonBin,
  ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000'],
  { cwd: backendDir, env: backendEnv, stdio: 'inherit' }
);

const frontend = spawn(
  'npm',
  ['run', 'dev', '--', '--host', '127.0.0.1', '--port', '5173'],
  { cwd: frontendDir, env: frontendEnv, stdio: 'inherit' }
);

const waitForUrl = (url, timeoutMs = 120000) => new Promise((resolve, reject) => {
  const start = Date.now();
  const check = () => {
    const req = http.get(url, (res) => {
      res.resume();
      if (res.statusCode && res.statusCode >= 200 && res.statusCode < 500) {
        resolve();
      } else {
        retry();
      }
    });
    req.on('error', retry);
  };

  const retry = () => {
    if (Date.now() - start > timeoutMs) {
      reject(new Error(`Timeout waiting for ${url}`));
      return;
    }
    setTimeout(check, 1000);
  };

  check();
});

const shutdown = () => {
  if (!backend.killed) backend.kill('SIGTERM');
  if (!frontend.killed) frontend.kill('SIGTERM');
  process.exit(0);
};

process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);

backend.on('exit', (code) => {
  if (code !== 0) {
    console.error(`Backend exited with code ${code}`);
    shutdown();
  }
});

frontend.on('exit', (code) => {
  if (code !== 0) {
    console.error(`Frontend exited with code ${code}`);
    shutdown();
  }
});

Promise.all([
  waitForUrl('http://127.0.0.1:8000/health'),
  waitForUrl('http://127.0.0.1:5173'),
])
  .then(() => {
    console.log('E2E servers ready.');
  })
  .catch((err) => {
    console.error(err.message);
    shutdown();
  });
