import { spawn, spawnSync } from 'node:child_process';
import process from 'node:process';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { existsSync } from 'node:fs';

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = resolve(__dirname, '..');

const backendDir = resolve(root, 'backend');
const frontendDir = resolve(root, 'datathon');

const isWindows = process.platform === 'win32';

// -----------------------------------------------------
// Detect Python
// -----------------------------------------------------

let pythonCommand;
let pythonArgs = [];

if (isWindows) {
  if (spawnSync('where', ['py'], { stdio: 'ignore' }).status === 0) {
    pythonCommand = 'py';
    pythonArgs = ['-3'];
  } else if (spawnSync('where', ['python'], { stdio: 'ignore' }).status === 0) {
    pythonCommand = 'python';
  } else {
    console.error('\n❌ Python 3 was not found.');
    console.error('Install Python from https://python.org/downloads\n');
    process.exit(1);
  }
} else {
  if (spawnSync('which', ['python3'], { stdio: 'ignore' }).status === 0) {
    pythonCommand = 'python3';
  } else if (spawnSync('which', ['python'], { stdio: 'ignore' }).status === 0) {
    pythonCommand = 'python';
  } else {
    console.error('\n❌ Python 3 was not found.');
    process.exit(1);
  }
}

// -----------------------------------------------------
// Install Backend Dependencies
// -----------------------------------------------------

// const requirements = resolve(backendDir, 'requirements.txt');

// if (!existsSync(requirements)) {
//   console.error('\n❌ backend/requirements.txt not found.\n');
//   process.exit(1);
// }

// console.log('\n📦 Installing backend dependencies...\n');

// const install = spawnSync(
//   pythonCommand,
//   [
//     ...pythonArgs,
//     '-m',
//     'pip',
//     'install',
//     '--disable-pip-version-check',
//     '-r',
//     'requirements.txt',
//   ],
//   {
//     cwd: backendDir,
//     stdio: 'inherit',
//     shell: isWindows,
//   }
// );

// if (install.status !== 0) {
//   console.error('\n❌ Failed to install backend dependencies.\n');
//   process.exit(install.status ?? 1);
// }

// console.log('\n✅ Backend dependencies are up to date.\n');

// -----------------------------------------------------
// Commands
// -----------------------------------------------------

const commands = [
  {
    label: 'backend',
    command: pythonCommand,
    args: [
      ...pythonArgs,
      '-m',
      'uvicorn',
      'app.main:app',
      '--reload',
      '--host',
      '0.0.0.0',
      '--port',
      '8000',
    ],
    cwd: backendDir,
  },
  {
    label: 'frontend',
    command: isWindows ? 'npm.cmd' : 'npm',
    args: ['run', 'dev'],
    cwd: frontendDir,
  },
];

// -----------------------------------------------------
// Process Management
// -----------------------------------------------------

const children = [];

function shutdown(exitCode = 0) {
  console.log('\n🛑 Shutting down...\n');

  for (const child of children) {
    if (child && !child.killed) {
      try {
        child.kill('SIGTERM');
      } catch (_) {}
    }
  }

  process.exit(exitCode);
}

// -----------------------------------------------------
// Start Processes
// -----------------------------------------------------

for (const { label, command, args, cwd } of commands) {
  console.log(`🚀 Starting ${label}...\n`);

  const child = spawn(command, args, {
    cwd,
    stdio: 'inherit',
    shell: isWindows,
  });

  child.on('error', (err) => {
    console.error(`\n❌ Failed to start ${label}`);
    console.error(err.message);
    shutdown(1);
  });

  child.on('exit', (code, signal) => {
    if (signal || (code !== null && code !== 0)) {
      console.error(
        `\n❌ ${label} exited ${
          signal ? `with signal ${signal}` : `with code ${code}`
        }`
      );

      shutdown(code ?? 1);
    }
  });

  console.log(`✅ ${label} started.\n`);

  children.push(child);
}

// -----------------------------------------------------
// Graceful Shutdown
// -----------------------------------------------------

process.on('SIGINT', () => shutdown(0));
process.on('SIGTERM', () => shutdown(0));
