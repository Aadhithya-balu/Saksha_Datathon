import { spawn } from 'node:child_process';
import process from 'node:process';

import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const isWindows = process.platform === 'win32';

// Use the .venv Python so all backend packages are available
const venvPython = isWindows
  ? path.resolve(__dirname, '..', '.venv', 'Scripts', 'python.exe')
  : path.resolve(__dirname, '..', '.venv', 'bin', 'python');

const pythonCommand = venvPython;
const pythonArgs = [];
const frontendCommand = isWindows ? 'cmd.exe' : 'npm';
const frontendArgs = isWindows
  ? ['/c', 'npm', 'run', 'dev', '--prefix', 'datathon']
  : ['run', 'dev', '--prefix', 'datathon'];

const commands = [
  {
    label: 'backend',
    command: pythonCommand,
    args: [...pythonArgs, '-m', 'uvicorn', 'app.main:app', '--reload'],
    cwd: 'backend',
  },
  {
    label: 'frontend',
    command: frontendCommand,
    args: frontendArgs,
  },
];

const children = commands.map(({ label, command, args, cwd }) => {
  const child = spawn(command, args, {
    stdio: 'inherit',
    shell: false,
    cwd: cwd ?? undefined,
  });

  child.on('exit', (code, signal) => {
    if (signal || code !== 0) {
      shutdown(signal ? 1 : code ?? 1);
    }
  });

  console.log(`[dev:all] started ${label}`);
  return child;
});

const shutdown = (exitCode = 0) => {
  for (const child of children) {
    if (!child.killed) {
      child.kill();
    }
  }
  process.exit(exitCode);
};

process.on('SIGINT', () => shutdown(0));
process.on('SIGTERM', () => shutdown(0));
