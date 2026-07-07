import { spawn } from 'node:child_process';
import process from 'node:process';

const isWindows = process.platform === 'win32';
const pythonCommand = isWindows ? 'py' : 'python';
const pythonArgs = isWindows ? ['-3.12'] : [];
const frontendCommand = isWindows ? 'cmd.exe' : 'npm';
const frontendArgs = isWindows
  ? ['/c', 'npm', 'run', 'dev', '--prefix', 'datathon']
  : ['run', 'dev', '--prefix', 'datathon'];

const commands = [
  {
    label: 'backend',
    command: pythonCommand,
    args: [...pythonArgs, '-m', 'uvicorn', 'app.main:app', '--reload', '--app-dir', 'backend'],
  },
  {
    label: 'frontend',
    command: frontendCommand,
    args: frontendArgs,
  },
];

const children = commands.map(({ label, command, args }) => {
  const child = spawn(command, args, {
    stdio: 'inherit',
    shell: false,
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
