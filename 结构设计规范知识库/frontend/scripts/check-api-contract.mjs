import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'

const contractPaths = ['openapi.json', 'src/generated/api']
const generatorEntry = fileURLToPath(
  new URL('../node_modules/@hey-api/openapi-ts/bin/run.js', import.meta.url),
)

function run(command, args, options = {}) {
  const result = spawnSync(command, args, {
    cwd: process.cwd(),
    encoding: 'utf8',
    stdio: options.capture ? 'pipe' : 'inherit',
  })
  if (result.error) throw result.error
  return result
}

const generation = run(process.execPath, [generatorEntry])
if (generation.status !== 0) process.exit(generation.status ?? 1)

const diff = run('git', ['diff', '--exit-code', '--', ...contractPaths])
if (diff.status !== 0) {
  console.error('Generated API contract differs from the Git index. Regenerate and commit it.')
  process.exit(diff.status ?? 1)
}

const untracked = run(
  'git',
  ['ls-files', '--others', '--exclude-standard', '--', ...contractPaths],
  { capture: true },
)
if (untracked.status !== 0) process.exit(untracked.status ?? 1)

const untrackedFiles = untracked.stdout.trim()
if (untrackedFiles) {
  console.error(`Generated API contract contains untracked files:\n${untrackedFiles}`)
  process.exit(1)
}

console.log('Generated API contract matches the Git index.')
