#!/usr/bin/env node
/** Compile an explicit OpenAPI journey. Dry runs use supplied fixture responses only. */
import fs from 'node:fs'
import path from 'node:path'
import { createRequire } from 'node:module'
import { fileURLToPath } from 'node:url'

const ownFile = fileURLToPath(import.meta.url)
const methods = new Set(['get', 'head', 'post', 'put', 'patch', 'delete', 'options', 'trace'])
const profiles = ['01-smoke', '02-load-pre-uat', '03-stress-spike']
const record = value => value !== null && typeof value === 'object' && !Array.isArray(value)

function readSpec(file) {
  const text = fs.readFileSync(file, 'utf8').replace(/^\uFEFF/, '')
  if (file.toLowerCase().endsWith('.json')) return JSON.parse(text)
  // Resolve existing parsers relative to the service or the source checkout.
  for (const owner of [file, path.resolve(path.dirname(ownFile), '../../mcp-servers/package.json')]) {
    const require = createRequire(owner)
    let module
    try { module = require.resolve('yaml') } catch { continue }
    return require(module).parse(text)
  }
  throw Error('YAML parser unavailable. Supply the project-generated OpenAPI JSON or use the repository dependency.')
}

function inventory(spec) {
  if (!/^3\.(0|1)\.\d+$/.test(spec?.openapi) || !record(spec.paths)) throw Error('Expected OpenAPI 3.0/3.1 paths.')
  const operations = new Map()
  const unsupported = []
  for (const [route, item] of Object.entries(spec.paths)) {
    if (!record(item)) throw Error('Invalid path item: ' + route)
    if (item.$ref) { unsupported.push(route + ': resolve path item in project first'); continue }
    for (const [method, op] of Object.entries(item)) {
      if (!methods.has(method)) continue
      if (!record(op)) throw Error('Invalid operation: ' + method + ' ' + route)
      operations.set(method.toUpperCase() + ' ' + route, {route, method, item, op})
    }
  }
  return {operations, unsupported}
}

function compile(spec, operations, journey) {
  if (!record(journey) || !Array.isArray(journey.steps) || !journey.steps.length) throw Error('Select a nonempty ordered list of steps.')
  const captured = new Set()
  return journey.steps.map(step => {
    if (!record(step) || !operations.has(step.operation)) throw Error('Unknown selected operation: ' + step?.operation)
    const {route, method, item, op} = operations.get(step.operation)
    if (!/^\/(?!\/)/.test(route) || /[?#\\\s]/.test(route) || method === 'trace') throw Error('Unsupported target: ' + step.operation)
    if (!Number.isInteger(step.expect) || step.expect < 200 || step.expect > 299 ||
        !(Object.hasOwn(op.responses || {}, String(step.expect)) || Object.hasOwn(op.responses || {}, '2XX'))) {
      throw Error('Select a documented exact success status: ' + step.operation)
    }
    const parameters = [...(item.parameters || []), ...(op.parameters || [])]
    if (parameters.some(p => !record(p) || p.$ref || (p.required && p.in !== 'path'))) {
      throw Error('Resolve references and implement required query/header/cookie parameters before compiling ' + step.operation)
    }
    const security = op.security ?? spec.security ?? []
    if (!Array.isArray(security) || security.length) throw Error('Authentication requires project-specific setup: ' + step.operation)
    const bindings = step.path ?? {}
    if (!record(bindings)) throw Error('Invalid path bindings')
    const placeholders = [...route.matchAll(/\{([^}]+)\}/g)].map(match => match[1])
    if (Object.keys(bindings).some(key => !placeholders.includes(key))) throw Error('Unexpected path binding')
    for (const key of placeholders) {
      const binding = bindings[key]
      if (typeof binding !== 'string' || !binding.trim() || (binding.startsWith('$') && !captured.has(binding.slice(1)))) {
        throw Error('Missing path fixture or earlier capture: ' + key)
      }
    }
    if (op.requestBody?.$ref || (op.requestBody?.required && step.body === undefined)) throw Error('Supply a resolved body fixture: ' + step.operation)
    if (step.body !== undefined && !op.requestBody?.content?.['application/json']) throw Error('No JSON request body declared: ' + step.operation)
    if (step.capture !== undefined) {
      if (!record(step.capture) || !/^[A-Za-z][A-Za-z0-9_]*$/.test(step.capture.name) || captured.has(step.capture.name) ||
          typeof step.capture.field !== 'string' || !step.capture.field.length) throw Error('Invalid or duplicate capture')
      captured.add(step.capture.name)
    }
    return {method: method.toUpperCase(), route, expect: step.expect, path: bindings, body: step.body, capture: step.capture}
  })
}

// Shared by the dry-run adapter and the generated k6 module.
function runJourney(steps, request) {
  const captures = Object.create(null)
  for (const step of steps) {
    const pathname = step.route.replace(/\{([^}]+)\}/g, (_, key) => {
      const value = step.path[key]
      const resolved = String(value.startsWith('$') ? captures[value.slice(1)] : value)
      if (!resolved || resolved === '.' || resolved === '..') throw Error('Invalid path segment: ' + key)
      return encodeURIComponent(resolved)
    })
    const response = request(step.method, pathname, step.body, step.route)
    if (response.status !== step.expect) throw Error(step.method + ' ' + step.route + ': unexpected HTTP ' + response.status)
    if (step.capture) {
      const data = response.json()
      const value = data && Object.hasOwn(data, step.capture.field) ? data[step.capture.field] : undefined
      if (!(typeof value === 'string' && value.length) && !Number.isSafeInteger(value)) throw Error('Missing captured value: ' + step.capture.name)
      captures[step.capture.name] = value
    }
  }
}

function simulate(steps, fixtures) {
  if (!Array.isArray(fixtures) || fixtures.length !== steps.length) throw Error('One mock exchange per step required.')
  const observed = []
  runJourney(steps, (method, pathname, body) => {
    const sample = fixtures[observed.length]
    if (sample.method !== method || sample.path !== pathname) throw Error('Mock exchange does not match ' + method + ' ' + pathname)
    observed.push({method, path: pathname, body})
    return {status: sample.status, json: () => sample.response}
  })
  return observed
}

function script(steps, profile) {
  // Templates carry no inherited OpenAPI target, reusable credential or default load schedule.
  return `import http from 'k6/http'
import { check, fail } from 'k6'

const steps = ${JSON.stringify(steps)}
const profile = ${JSON.stringify(profile)}
export const options = { vus: 1, iterations: 1, maxRedirects: 0, thresholds: { checks: ['rate==1'] } }

${runJourney.toString()}

export default function () {
  if (!steps.length) fail('Draft: select and dry-run a journey first')
  const target = __ENV.BASE_URL
  if (!/^https?:\\/\\/(?:127\\.0\\.0\\.1|localhost|\\[::1\\])(?::[0-9]+)?$/.test(target || '')) fail('Supply an explicit loopback mock origin')
  if (__ENV.APPROVED_PROFILE !== profile) fail('Select the approved profile and fixture')
  try {
    runJourney(steps, (method, route, body, template) => http.request(method, target + route,
      body === undefined ? null : JSON.stringify(body), {redirects: 0, headers: {'Content-Type':'application/json'}, tags: {name:method + ' ' + template}}))
    check(true, {'journey satisfied contract': v => v})
  } catch (error) {
    check(false, {'journey satisfied contract': v => v})
    fail(String(error))
  }
}
`
}

function main(args) {
  const option = name => {
    const i = args.indexOf(name)
    if (i < 0) return undefined
    if (!args[i + 1] || args[i + 1].startsWith('--')) throw Error('Missing value for ' + name)
    return args[i + 1]
  }
  if (args.includes('--selftest')) {
    const fixture = {openapi:'3.1.0', paths:{'/sample':{get:{responses:{200:{description:'OK'}}}}}}
    const steps = compile(fixture, inventory(fixture).operations, {steps:[{operation:'GET /sample',expect:200}]})
    simulate(steps, [{method:'GET',path:'/sample',status:200}])
    return {status:'SELFTEST_OK', detectedEndpoints:1}
  }
  const input = option('--spec')
  if (!input) throw Error('Usage: --spec FILE [--journey FILE] [--out DIR | --dry-run] or --selftest')
  const spec = readSpec(path.resolve(input))
  const {operations, unsupported} = inventory(spec)
  const selection = option('--journey')
  const journey = selection && JSON.parse(fs.readFileSync(selection, 'utf8').replace(/^\uFEFF/, ''))
  const steps = journey ? compile(spec, operations, journey) : []
  const result = {status: 'DRAFT', detectedEndpoints: operations.size, operations: [...operations.keys()], unsupported, selected: steps.length, files: []}
  if (args.includes('--dry-run')) {
    if (!journey || option('--out')) throw Error('Dry-run needs --journey with mock exchanges and no --out.')
    return {...result, status:'MOCK_VERIFIED', exchanges:simulate(steps, journey.mock)}
  }
  const directory = path.resolve(option('--out') || 'tests/perf')
  const files = profiles.map(profile => path.join(directory, profile + '.k6.js'))
  if (files.some(file => fs.existsSync(file))) throw Error('Output exists; choose a new directory or review the existing suite.')
  if (journey) simulate(steps, journey.mock)
  fs.mkdirSync(directory, {recursive:true})
  const created = []
  try {
    for (const [i, file] of files.entries()) {
      const fd = fs.openSync(file, 'wx')
      created.push(file)
      try { fs.writeFileSync(fd, script(steps, profiles[i])) } finally { fs.closeSync(fd) }
    }
  } catch (error) {
    for (const file of created) fs.unlinkSync(file)
    throw error
  }
  return {...result, status: steps.length ? 'GENERATED' : 'DRAFT', files}
}

try { console.log(JSON.stringify(main(process.argv.slice(2)), null, 2)) }
catch (error) { console.error(error.message); process.exitCode = 1 }
