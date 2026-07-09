import { spawn } from 'node:child_process';
import process from 'node:process';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = resolve(__dirname, '..');

const isWindows = process.platform === 'win32';
const pythonCommand = isWindows ? 'py' : 'python3';
const pythonArgs = isWindows ? ['-3.12'] : [];

const commands = [
  {
    label: 'backend',
    command: pythonCommand,
    args: [...pythonArgs, '-m', 'uvicorn', 'app.main:app', '--reload', '--host', '0.0.0.0', '--port', '8000'],
    cwd: resolve(root, 'backend'),
  },
  {
    label: 'frontend',
    command: isWindows ? 'cmd.exe' : 'npm',
    args: isWindows ? ['/c', 'npm', 'run', 'dev'] : ['run', 'dev'],
    cwd: resolve(root, 'datathon'),
  },
];

const children = commands.map(({ label, command, args, cwd }) => {
  const child = spawn(command, args, {
    stdio: 'inherit',
    shell: false,
    cwd,
  });

  child.on('exit', (code, signal) => {
    if (signal || code !== 0) {
      shutdown(signal ? 1 : code ?? 1);
    }
  });

  console.log(`[dev:all] started ${label} in ${cwd}`);
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
