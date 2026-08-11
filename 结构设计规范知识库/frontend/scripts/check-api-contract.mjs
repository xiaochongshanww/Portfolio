import { spawnSync } from 'node:child_process'
import { readdirSync, readFileSync } from 'node:fs'
import { join, relative } from 'node:path'
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

function runtimeSourceFiles(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name)
    if (entry.isDirectory()) {
      return entry.name === 'generated' ? [] : runtimeSourceFiles(path)
    }
    if (!/\.(ts|vue)$/.test(entry.name) || entry.name.endsWith('.spec.ts')) return []
    return [path]
  })
}

function checkGeneratedClientBoundary() {
  const legacySymbol = /\b(?:adminGet|adminGetWithApiKey|adminPost|adminPatch|adminPut|adminDelete|adminBlobUrl|AdminGetPath|AdminPostPath|AdminPatchPath|AdminPutPath|AdminDeletePath|AdminBlobPath)\b/
  const directAdminPath = /['"`]\/admin\//
  const violations = []

  for (const path of runtimeSourceFiles('src')) {
    const text = readFileSync(path, 'utf8')
    if (legacySymbol.test(text)) violations.push(`${relative('.', path)}: legacy admin wrapper`)
    if (directAdminPath.test(text)) violations.push(`${relative('.', path)}: direct admin URL`)
  }

  if (violations.length) {
    console.error(`Admin calls must use the generated operation SDK:\n${violations.join('\n')}`)
    process.exit(1)
  }
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

checkGeneratedClientBoundary()
console.log('Generated API contract matches the Git index.')
