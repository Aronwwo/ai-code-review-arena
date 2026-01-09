#!/usr/bin/env node
/**
 * Setup script for AI Code Review Arena
 * Installs dependencies, runs migrations, and seeds admin account
 */

const { execSync, spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const ROOT = path.resolve(__dirname, '..');
const BACKEND = path.join(ROOT, 'backend');
const FRONTEND = path.join(ROOT, 'frontend');

const isWindows = process.platform === 'win32';
const pythonCmd = isWindows ? 'python' : 'python3';
const venvPython = isWindows
  ? path.join(BACKEND, 'venv', 'Scripts', 'python.exe')
  : path.join(BACKEND, 'venv', 'bin', 'python');
const venvPip = isWindows
  ? path.join(BACKEND, 'venv', 'Scripts', 'pip.exe')
  : path.join(BACKEND, 'venv', 'bin', 'pip');

function run(cmd, cwd = ROOT, options = {}) {
  console.log(`\n> ${cmd}`);
  try {
    execSync(cmd, {
      cwd,
      stdio: 'inherit',
      shell: true,
      ...options
    });
    return true;
  } catch (err) {
    console.error(`Command failed: ${cmd}`);
    return false;
  }
}

function checkCommand(cmd) {
  try {
    execSync(`${isWindows ? 'where' : 'which'} ${cmd}`, { stdio: 'pipe' });
    return true;
  } catch {
    return false;
  }
}

async function main() {
  console.log('========================================');
  console.log('  AI Code Review Arena - Setup');
  console.log('========================================\n');

  // Check Python
  if (!checkCommand(pythonCmd)) {
    console.error('ERROR: Python 3 is required but not found.');
    console.error('Please install Python 3.10+ from https://python.org');
    process.exit(1);
  }

  // Check Node
  if (!checkCommand('node')) {
    console.error('ERROR: Node.js is required but not found.');
    process.exit(1);
  }

  // 1. Setup Backend
  console.log('\n[1/5] Setting up backend...');

  // Create venv if not exists
  if (!fs.existsSync(path.join(BACKEND, 'venv'))) {
    console.log('Creating Python virtual environment...');
    run(`${pythonCmd} -m venv venv`, BACKEND);
  }

  // Install Python dependencies
  console.log('Installing Python dependencies...');
  run(`"${venvPip}" install -r requirements.txt`, BACKEND);

  // 2. Setup Frontend
  console.log('\n[2/5] Setting up frontend...');

  // Install npm dependencies
  run('npm install', FRONTEND);

  // 3. Run migrations
  console.log('\n[3/5] Running database migrations...');

  // Create data directory
  const dataDir = path.join(BACKEND, 'data');
  if (!fs.existsSync(dataDir)) {
    fs.mkdirSync(dataDir, { recursive: true });
  }

  // Run alembic migrations
  const alembicCmd = isWindows
    ? `"${path.join(BACKEND, 'venv', 'Scripts', 'alembic.exe')}" upgrade head`
    : `${path.join(BACKEND, 'venv', 'bin', 'alembic')} upgrade head`;
  run(alembicCmd, BACKEND);

  // 4. Seed admin account
  console.log('\n[4/5] Seeding admin account...');
  run(`"${venvPython}" scripts/seed_admin.py`, BACKEND);

  // 5. Check Ollama
  console.log('\n[5/5] Checking Ollama...');
  try {
    execSync('curl -s http://localhost:11434/api/tags', { stdio: 'pipe', timeout: 3000 });
    console.log('Ollama is running.');

    // Try to pull recommended model
    console.log('Attempting to pull qwen2.5-coder model (this may take a while)...');
    run('ollama pull qwen2.5-coder:latest', ROOT, { timeout: 600000 });
  } catch {
    console.log('Ollama is not running. The app will use MockProvider for testing.');
    console.log('To use local AI, install Ollama from https://ollama.ai');
  }

  // Done
  console.log('\n========================================');
  console.log('  Setup Complete!');
  console.log('========================================');
  console.log('\nAdmin Credentials:');
  console.log('  Email:    admin@local.test');
  console.log('  Password: Admin123!');
  console.log('  Username: admin');
  console.log('\nNext steps:');
  console.log('  1. Run: npm run dev');
  console.log('  2. Open: http://localhost:5173 (frontend)');
  console.log('  3. API docs: http://localhost:8000/docs');
  console.log('\nOllama (optional):');
  console.log('  - Install from https://ollama.ai');
  console.log('  - Run: ollama pull qwen2.5-coder');
  console.log('========================================\n');
}

main().catch(err => {
  console.error('Setup failed:', err);
  process.exit(1);
});
