#!/usr/bin/env node
/**
 * Dev script for AI Code Review Arena
 * Starts both frontend and backend concurrently
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const ROOT = path.resolve(__dirname, '..');
const BACKEND = path.join(ROOT, 'backend');
const FRONTEND = path.join(ROOT, 'frontend');

const isWindows = process.platform === 'win32';

function startProcess(name, cmd, args, cwd, color) {
  const colorCodes = {
    blue: '\x1b[34m',
    green: '\x1b[32m',
    reset: '\x1b[0m'
  };

  const prefix = `${colorCodes[color]}[${name}]${colorCodes.reset}`;

  const proc = spawn(cmd, args, {
    cwd,
    shell: true,
    stdio: ['inherit', 'pipe', 'pipe']
  });

  proc.stdout.on('data', (data) => {
    const lines = data.toString().split('\n');
    lines.forEach(line => {
      if (line.trim()) {
        console.log(`${prefix} ${line}`);
      }
    });
  });

  proc.stderr.on('data', (data) => {
    const lines = data.toString().split('\n');
    lines.forEach(line => {
      if (line.trim()) {
        console.error(`${prefix} ${line}`);
      }
    });
  });

  proc.on('error', (err) => {
    console.error(`${prefix} Failed to start: ${err.message}`);
  });

  proc.on('close', (code) => {
    if (code !== 0 && code !== null) {
      console.log(`${prefix} Process exited with code ${code}`);
    }
  });

  return proc;
}

async function main() {
  console.log('========================================');
  console.log('  AI Code Review Arena - Development');
  console.log('========================================\n');

  // Check if dependencies are installed
  if (!fs.existsSync(path.join(FRONTEND, 'node_modules'))) {
    console.error('Frontend dependencies not installed. Run: npm run setup');
    process.exit(1);
  }

  if (!fs.existsSync(path.join(BACKEND, 'venv'))) {
    console.error('Backend venv not found. Run: npm run setup');
    process.exit(1);
  }

  const processes = [];

  // Start backend
  console.log('Starting backend on http://localhost:8000');
  const uvicornPath = isWindows
    ? path.join(BACKEND, 'venv', 'Scripts', 'uvicorn.exe')
    : path.join(BACKEND, 'venv', 'bin', 'uvicorn');

  const backend = startProcess(
    'BACKEND',
    `"${uvicornPath}"`,
    ['app.main:app', '--reload', '--host', '0.0.0.0', '--port', '8000'],
    BACKEND,
    'blue'
  );
  processes.push(backend);

  // Start frontend
  console.log('Starting frontend on http://localhost:5173');
  const frontend = startProcess(
    'FRONTEND',
    'npm',
    ['run', 'dev'],
    FRONTEND,
    'green'
  );
  processes.push(frontend);

  console.log('\n----------------------------------------');
  console.log('  Frontend: http://localhost:5173');
  console.log('  Backend:  http://localhost:8000');
  console.log('  API Docs: http://localhost:8000/docs');
  console.log('----------------------------------------');
  console.log('Press Ctrl+C to stop all servers\n');

  // Handle Ctrl+C
  process.on('SIGINT', () => {
    console.log('\nShutting down...');
    processes.forEach(proc => {
      if (isWindows) {
        spawn('taskkill', ['/pid', proc.pid, '/f', '/t'], { shell: true });
      } else {
        proc.kill('SIGTERM');
      }
    });
    process.exit(0);
  });

  // Keep process alive
  process.stdin.resume();
}

main().catch(err => {
  console.error('Dev server failed:', err);
  process.exit(1);
});
