import path from 'node:path'

function localPath(from, target) {
  if (!/^[\w./-]+$/.test(target) || target.startsWith('/')) return null
  const file = path.posix.join(path.posix.dirname(from), target)
  return file === '..' || file.startsWith('../') ? null : file
}

function imports(code, from, records) {
  return Array.from(code.matchAll(/\bimport\s+\{([^{}]+)\}\s+from\s*['"](\.[^'"]+)['"]/g), ([, names, target]) => {
    const file = localPath(from, target)
    const source = file && [file, file.replace(/\.m?js$/, '.ts'), `${file}.ts`].find((candidate) => records.has(candidate))
    return { source, names: names.split(',').map((name) => name.trim()).filter((name) => /^\w+$/.test(name)) }
  }).filter(({ source }) => source)
}

function inspectWriter(entry, configuration, records) {
  const code = records.get(entry)
  if (!code || !/\bimport\s+\{[^{}]*\bwriteFile(?:Sync)?\b[^{}]*\}\s+from\s*['"](?:node:)?fs(?:\/promises)?['"]/.test(code)) return null
  const serialized = code.match(/\bconst\s+(\w+)\s*=\s*JSON\.stringify\(\s*(\w+)\s*\(/)
  const write = code.match(/\bwriteFile(?:Sync)?\(\s*(\w+)\s*,\s*(\w+)\s*[,)]/)
  if (!serialized || !write || serialized[1] !== write[2]) return null
  const destination = Array.from(code.matchAll(/\bconst\s+(\w+)\s*=\s*(?:resolve\(\s*)?['"]([\w.\/-]+\.json)['"]/g))
    .find(([, name]) => name === write[1])
  const output = destination && localPath(configuration, destination[2])
  const symbol = serialized[2]
  const producer = imports(code, entry, records).find(({ names }) => names.includes(symbol))?.source
  if (!output || !producer) return null
  const sourceCode = records.get(producer)
  const declared = new RegExp(`\\bexport\\s+(?:function|const)\\s+${symbol}\\b`).test(sourceCode)
  if (!declared || !/\bopenapi\s*:\s*['"]3\.\d+\.\d+['"]/.test(sourceCode) || !/\bpaths\s*[:,}]/.test(sourceCode)) return null
  const inputs = imports(sourceCode, producer, records)
    .filter(({ names }) => names.some((name) => /(?:endpoint|route)(?:Registry|Policy|Definitions|Schema)/i.test(name)
      && new RegExp(`\\b${name}\\b[\\s\\S]*\\b${name}\\b`).test(sourceCode)))
    .map(({ source }) => source)
  return { producer, symbol, output, inputs }
}

export function findRepositoryGenerators(records) {
  const workflows = new Map()
  const sourceRecords = new Map(records.map(({ file, code }) => [file, code]))
  for (const { file, raw } of records) {
    if (path.posix.basename(file) !== 'package.json') continue
    let manifest
    try {
      manifest = JSON.parse(raw)
    } catch {
      continue
    }
    for (const [script, command] of Object.entries(manifest?.scripts || {})) {
      if (typeof command !== 'string' || !/^[\w:-]+$/.test(script)) continue
      const launch = command.match(/^\s*(?:node|tsx|ts-node)\s+['"]?([\w./-]+\.[cm]?[jt]s)['"]?(\s+--check)?\s*$/)
      const entry = launch && localPath(file, launch[1])
      if (!entry) continue
      const writer = inspectWriter(entry, file, sourceRecords)
      if (!writer) continue
      const key = JSON.stringify([writer.producer, writer.symbol])
      const workflow = workflows.get(key) || {
        producer: writer.producer,
        symbol: writer.symbol,
        inputs: writer.inputs,
        framework: Object.hasOwn(manifest.dependencies || {}, 'express') ? 'express' : null,
        entryPoints: new Set(),
        outputPaths: new Set(),
        commands: [],
      }
      workflow.entryPoints.add(entry)
      workflow.outputPaths.add(writer.output)
      workflow.commands.push({ configuration: file, script, mode: launch[2] ? 'CHECK' : 'GENERATE' })
      workflows.set(key, workflow)
    }
  }
  return [...workflows.values()].filter(({ commands }) => commands.some(({ mode }) => mode === 'GENERATE'))
    .map((workflow) => ({ ...workflow, entryPoints: [...workflow.entryPoints], outputPaths: [...workflow.outputPaths] }))
}

export function servesRepositoryGenerator(viewerFile, endpoint, workflow, records) {
  const code = records.get(viewerFile)
  if (!code || !imports(code, viewerFile, records).some(({ source, names }) => source === workflow.producer && names.includes(workflow.symbol))) return false
  const callable = workflow.symbol
  const result = code.match(new RegExp(`\\bconst\\s+(\\w+)\\s*=\\s*${callable}\\s*\\(`))?.[1]
  if (!result) return false
  for (const mounted of code.matchAll(/\bmountEndpoint\(\s*\w+\s*,\s*['"]([\w.-]+)['"]([\s\S]*?)\n\s*\}\s*\);/g)) {
    const [, id, handler] = mounted
    if (!new RegExp(`\\.json\\(\\s*${result}\\s*\\)`).test(handler)) continue
    const registered = workflow.inputs.some((input) => {
      const entry = Array.from(records.get(input).matchAll(/['"]([\w.-]+)['"]\s*:\s*\{[^{}]*?\bpath\s*:\s*['"]([^'"]+)['"]/g))
        .find(([, routeId]) => routeId === id)
      return entry?.[2] === endpoint
    })
    if (registered) return true
  }
  return false
}
