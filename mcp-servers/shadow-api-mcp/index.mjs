#!/usr/bin/env node
/**
 * Shadow API & OpenAPI MCP Server (shadow-api-mcp v1.1.0)
 * Cross-agent (Antigravity, Claude Code, Codex, Gemini CLI) MCP server for:
 * 1. Real HTTP API testing against live local/remote backends (test_api_endpoint)
 * 2. Adaptive OpenAPI 3.1.0 architecture:
 *    - Compact mode (small projects): docs/api/openapi.yaml
 *    - Modular mode (large/multi-module projects): docs/api/modules/<module>.openapi.yaml + auto-bundled docs/api/openapi.yaml
 * 3. Generating & syncing nested Postman Collection v2.1 + Environment (sync_postman_collection)
 * 4. Validating & running live smoke tests across endpoints (validate_openapi_spec, run_api_collection)
 */

import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import readline from 'node:readline'
import YAML from 'yaml'

const PROTOCOL_VERSION = '2024-11-05'
const SERVER_INFO = {
  name: 'shadow-api-mcp',
  version: '1.2.0',
}

const METHOD_SORT_ORDER = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']

const TOOLS = [
  {
    name: 'test_api_endpoint',
    description:
      'Execute a real HTTP request (GET, POST, PUT, PATCH, DELETE) against a live local or remote API endpoint, measure latency, inspect status/headers/body, and optionally record the endpoint and real response directly into OpenAPI (compact or modular).',
    inputSchema: {
      type: 'object',
      properties: {
        url: {
          type: 'string',
          description: 'Full URL to call, e.g. http://localhost:3000/api/v1/users',
        },
        method: {
          type: 'string',
          enum: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'],
          description: 'HTTP method',
        },
        headers: {
          type: 'object',
          additionalProperties: { type: 'string' },
          description: 'Optional HTTP request headers',
        },
        queryParams: {
          type: 'object',
          additionalProperties: { type: 'string' },
          description: 'Optional query string parameters',
        },
        bearerToken: {
          type: 'string',
          description: 'Optional Bearer token for Authorization header',
        },
        body: {
          description: 'Optional JSON object or raw string request body',
        },
        expectedStatus: {
          type: 'number',
          description: 'Optional expected HTTP status code (e.g. 200, 201)',
        },
        timeoutMs: {
          type: 'number',
          description: 'Request timeout in milliseconds (default: 15000)',
        },
        recordToOpenApiPath: {
          type: 'string',
          description:
            'Optional path to master openapi.yaml (e.g. <project>/docs/api/openapi.yaml). Automatically records this endpoint and real response.',
        },
        moduleName: {
          type: 'string',
          description:
            'Optional module slug for multi-module projects (e.g. "auth", "users", "finance-invoices"). When set (or when docs/api/modules/ exists), writes to docs/api/modules/<moduleName>.openapi.yaml and auto-bundles the master openapi.yaml.',
        },
        routePattern: {
          type: 'string',
          description:
            'OpenAPI route pattern when recording (e.g. /api/v1/users/{id}). Defaults to URL pathname.',
        },
        summary: {
          type: 'string',
          description: 'Short endpoint summary when recording to OpenAPI',
        },
        tag: {
          type: 'string',
          description:
            'OpenAPI / Postman folder tag. Supports nested Postman folders with "/" (e.g. "Master Data/Users" or "Auth").',
        },
      },
      required: ['url', 'method'],
    },
  },
  {
    name: 'discover_api_artifacts',
    description:
      'Read-only discovery of all existing OpenAPI/Swagger files, modular spec folders (modules/, paths/, domains/, specs/), and API client collections (Bruno, Postman, Insomnia, Hoppscotch, Thunder Client, .http/.rest) anywhere in the project before reading, updating, or generating files.',
    inputSchema: {
      type: 'object',
      properties: {
        projectRoot: {
          type: 'string',
          description: 'Absolute path to the project root (or any path inside the project).',
        },
      },
      required: ['projectRoot'],
    },
  },
  {
    name: 'upsert_openapi_endpoint',
    description:
      'Create or update an endpoint definition in the project OpenAPI specification. Auto-discovers existing OpenAPI/Swagger files (.yaml/.yml/.json) and modular folders (modules/, paths/, domains/, specs/) to avoid duplicates, and preserves single-file layouts unless allowAutoSplit or moduleName is passed.',
    inputSchema: {
      type: 'object',
      properties: {
        specPath: {
          type: 'string',
          description:
            'Absolute path to the OpenAPI/Swagger spec (.yaml/.yml/.json). If missing on disk, resolves against an existing project OpenAPI spec when unambiguous.',
        },
        projectRoot: {
          type: 'string',
          description: 'Optional explicit project root for discovering existing specs/collections.',
        },
        allowNewSpec: {
          type: 'boolean',
          description: 'Set true only when intentionally creating an additional spec file alongside existing ones.',
        },
        moduleName: {
          type: 'string',
          description:
            'Optional module slug for modular specs. Writes into the existing modular folder/extension convention (or modules/<moduleName>.openapi.yaml) and bundles into master specPath.',
        },
        autoModularThreshold: {
          type: 'number',
          description:
            'Tag count threshold for splitting new compact specs (default: 4; set 0 to disable). Existing single-file specs are NOT split unless allowAutoSplit=true.',
        },
        allowAutoSplit: {
          type: 'boolean',
          description: 'Allow splitting an existing single-file spec when tags exceed autoModularThreshold (default: false).',
        },
        title: {
          type: 'string',
          description: 'API title (used when initializing a new OpenAPI file)',
        },
        serverUrl: {
          type: 'string',
          description: 'Base server URL, e.g. http://localhost:3000',
        },
        routePath: {
          type: 'string',
          description: 'OpenAPI route path, e.g. /api/v1/users/{id}',
        },
        method: {
          type: 'string',
          enum: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'],
          description: 'HTTP method',
        },
        summary: {
          type: 'string',
          description: 'Endpoint summary',
        },
        description: {
          type: 'string',
          description: 'Detailed endpoint description',
        },
        tags: {
          type: 'array',
          items: { type: 'string' },
          description:
            'Endpoint tags. Supports nested folder paths like ["Master Data/Users"] or ["Orders"].',
        },
        requiresAuth: {
          type: 'boolean',
          description: 'Whether endpoint requires Bearer JWT authentication',
        },
        pathParams: {
          type: 'array',
          items: {
            type: 'object',
            properties: {
              name: { type: 'string' },
              type: { type: 'string' },
              description: { type: 'string' },
              example: { type: 'string' },
            },
            required: ['name'],
          },
        },
        queryParams: {
          type: 'array',
          items: {
            type: 'object',
            properties: {
              name: { type: 'string' },
              type: { type: 'string' },
              required: { type: 'boolean' },
              description: { type: 'string' },
              example: { type: 'string' },
            },
            required: ['name'],
          },
        },
        requestExample: {
          description:
            'Example JSON payload for requestBody (schema is inferred if requestSchema is omitted)',
        },
        requestSchema: {
          type: 'object',
          description: 'Explicit JSON Schema for requestBody',
        },
        responses: {
          type: 'object',
          description:
            'Map of status code (e.g. "200", "400") to { description, example, schema }',
        },
      },
      required: ['specPath', 'routePath', 'method', 'summary'],
    },
  },
  {
    name: 'bulk_upsert_openapi_endpoints',
    description:
      'Batch-create or update multiple endpoints in OpenAPI (.yaml/.yml/.json). Auto-discovers existing OpenAPI specs/folders and existing API client collections (Bruno, Postman, Insomnia, Hoppscotch, .http) across the project; only generates/updates Postman when Postman is the project convention or collectionFormat="postman".',
    inputSchema: {
      type: 'object',
      properties: {
        specPath: {
          type: 'string',
          description: 'Absolute path to OpenAPI/Swagger spec (.yaml/.yml/.json). Resolves to existing spec when unambiguous.',
        },
        projectRoot: {
          type: 'string',
          description: 'Optional explicit project root for discovering existing specs/collections.',
        },
        allowNewSpec: {
          type: 'boolean',
          description: 'Set true only when intentionally creating a new spec file alongside existing ones.',
        },
        allowAutoSplit: {
          type: 'boolean',
          description: 'Allow auto-splitting an existing single-file spec when tags exceed threshold (default: false).',
        },
        title: {
          type: 'string',
          description: 'API title',
        },
        serverUrl: {
          type: 'string',
          description: 'Base server URL, e.g. http://localhost:3000',
        },
        autoSyncPostman: {
          type: 'boolean',
          description: 'Deprecated. false is equivalent to collectionFormat="none". Prefer collectionFormat.',
        },
        collectionFormat: {
          type: 'string',
          enum: ['auto', 'postman', 'bruno', 'none'],
          description: 'API client collection handling. "auto" (default) detects existing collections anywhere in the project and only updates Postman when Postman is already used; "postman" forces Postman; "bruno"/"none" generate no Postman files.',
        },
        endpoints: {
          type: 'array',
          description: 'Array of endpoint definitions extracted from the existing backend routes/controllers/DTOs',
          items: {
            type: 'object',
            properties: {
              moduleName: { type: 'string' },
              routePath: { type: 'string' },
              method: { type: 'string', enum: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'] },
              summary: { type: 'string' },
              description: { type: 'string' },
              tags: { type: 'array', items: { type: 'string' } },
              requiresAuth: { type: 'boolean' },
              pathParams: { type: 'array', items: { type: 'object' } },
              queryParams: { type: 'array', items: { type: 'object' } },
              requestExample: {},
              requestSchema: { type: 'object' },
              responses: { type: 'object' },
            },
            required: ['routePath', 'method', 'summary'],
          },
        },
      },
      required: ['specPath', 'endpoints'],
    },
  },
  {
    name: 'sync_postman_collection',
    description:
      'Generate or update a Postman Collection v2.1.0 and Environment from an OpenAPI/Swagger spec. Detects existing Postman collections anywhere in the project to update in-place, and refuses on Bruno/Insomnia/etc. projects unless force=true.',
    inputSchema: {
      type: 'object',
      properties: {
        specPath: {
          type: 'string',
          description: 'Absolute path to OpenAPI/Swagger spec (.yaml/.yml/.json)',
        },
        projectRoot: {
          type: 'string',
          description: 'Optional explicit project root for discovering existing specs/collections.',
        },
        collectionOutputPath: {
          type: 'string',
          description:
            'Optional output path (defaults to existing detected Postman collection path, or next to specPath)',
        },
        environmentOutputPath: {
          type: 'string',
          description: 'Optional output path for postman_environment.json',
        },
        baseUrl: {
          type: 'string',
          description: 'Default baseUrl variable value (e.g. http://localhost:3000)',
        },
        force: {
          type: 'boolean',
          description: 'Only set when the Monarch explicitly requested Postman. Without it, the tool refuses if the project already uses Bruno/Insomnia/etc.',
        },
      },
      required: ['specPath'],
    },
  },
  {
    name: 'validate_openapi_spec',
    description:
      'Validate and audit an OpenAPI/Swagger specification (and any modular files under modules/, paths/, domains/, endpoints/, specs/), auto-resolving existing project spec paths when unambiguous.',
    inputSchema: {
      type: 'object',
      properties: {
        specPath: {
          type: 'string',
          description: 'Absolute path to OpenAPI/Swagger spec (.yaml/.yml/.json)',
        },
        projectRoot: {
          type: 'string',
          description: 'Optional explicit project root for discovering existing specs.',
        },
      },
      required: ['specPath'],
    },
  },
  {
    name: 'run_api_collection',
    description:
      'Run automated live HTTP smoke tests for all (or tag/module-filtered) endpoints defined in an OpenAPI/Swagger file (.yaml/.yml/.json) against a target baseUrl.',
    inputSchema: {
      type: 'object',
      properties: {
        specPath: {
          type: 'string',
          description: 'Absolute path to OpenAPI/Swagger spec (.yaml/.yml/.json)',
        },
        projectRoot: {
          type: 'string',
          description: 'Optional explicit project root for discovering existing specs.',
        },
        baseUrl: {
          type: 'string',
          description: 'Target live server URL, e.g. http://localhost:3000',
        },
        bearerToken: {
          type: 'string',
          description: 'Optional Bearer token for authenticated endpoints',
        },
        tagFilter: {
          type: 'string',
          description: 'Optional tag name (or prefix) to run only a subset of endpoints',
        },
        onlyGetRequests: {
          type: 'boolean',
          description: 'If true, only executes safe GET requests',
        },
      },
      required: ['specPath', 'baseUrl'],
    },
  },
]

function sanitizeSlug(input) {
  return String(input || 'general')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '') || 'general'
}

function inferJsonSchema(value) {
  if (value === null || value === undefined) {
    return { type: 'null' }
  }
  if (Array.isArray(value)) {
    return {
      type: 'array',
      items: value.length > 0 ? inferJsonSchema(value[0]) : { type: 'object' },
    }
  }
  const t = typeof value
  if (t === 'string') return { type: 'string', example: value }
  if (t === 'number')
    return { type: Number.isInteger(value) ? 'integer' : 'number', example: value }
  if (t === 'boolean') return { type: 'boolean', example: value }
  if (t === 'object') {
    const properties = {}
    const required = []
    for (const [k, v] of Object.entries(value)) {
      properties[k] = inferJsonSchema(v)
      if (v !== null && v !== undefined) required.push(k)
    }
    const schema = { type: 'object', properties }
    if (required.length > 0) schema.required = required
    return schema
  }
  return { type: 'string' }
}

function createEmptySpec(defaults = {}) {
  return {
    openapi: '3.1.0',
    info: {
      title: defaults.title || 'Project API Specification',
      version: '1.0.0',
      description: 'Source-verified OpenAPI 3.1.0 contract managed by Shadow Army.',
    },
    servers: [
      {
        url: defaults.serverUrl || 'http://localhost:3000',
        description: 'Local Development Server',
      },
    ],
    tags: [],
    components: {
      securitySchemes: {
        BearerAuth: {
          type: 'http',
          scheme: 'bearer',
          bearerFormat: 'JWT',
        },
      },
      schemas: {},
    },
    paths: {},
  }
}

const IGNORED_SCAN_DIRS = new Set([
  'node_modules',
  '.git',
  'dist',
  'build',
  'out',
  '.next',
  '.nuxt',
  '.svelte-kit',
  'vendor',
  'venv',
  '.venv',
  '__pycache__',
  'coverage',
  'target',
])
const MODULAR_SUBDIR_NAMES = ['modules', 'paths', 'domains', 'endpoints', 'specs']
const ROOT_MANIFEST_FILES = new Set([
  'package.json',
  'pyproject.toml',
  'go.mod',
  'composer.json',
  'Cargo.toml',
  'pom.xml',
  'build.gradle',
  'build.gradle.kts',
  'bruno.json',
])
const SPEC_CONTAINER_DIR_NAMES = new Set([
  'api',
  'apis',
  'docs',
  'doc',
  'openapi',
  'swagger',
  'specs',
  'spec',
  'contracts',
  'contract',
  'postman',
  'bruno',
  'collections',
])
const SKIP_SPEC_BASENAME_RE =
  /^(?:package(?:-lock)?|pnpm-lock|yarn|tsconfig.*|jsconfig.*|composer|cargo|pyproject|bruno|eslint.*|prettier.*|jest\.config.*|vitest\.config.*|docker-compose.*|.*postman_(?:collection|environment))\.(?:json|ya?ml)$/i

function isJsonPath(filePath) {
  return String(filePath || '').trim().toLowerCase().endsWith('.json')
}

function getSpecExtension(filePath) {
  const lower = String(filePath || '').trim().toLowerCase()
  if (lower.endsWith('.json')) return '.json'
  if (lower.endsWith('.yml')) return '.yml'
  return '.yaml'
}

function safeReadText(filePath, maxBytes = 8 * 1024 * 1024) {
  try {
    const stat = fs.statSync(filePath)
    if (!stat.isFile() || stat.size > maxBytes) return null
    return fs.readFileSync(filePath, 'utf8')
  } catch {
    return null
  }
}

function parseOpenApiCandidate(filePath) {
  const base = path.basename(filePath)
  const lower = base.toLowerCase()
  if (!lower.endsWith('.yaml') && !lower.endsWith('.yml') && !lower.endsWith('.json')) return null
  if (SKIP_SPEC_BASENAME_RE.test(lower)) return null
  const raw = safeReadText(filePath)
  if (!raw) return null
  try {
    const parsed = lower.endsWith('.json') ? JSON.parse(raw) : YAML.parse(raw)
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return null
    if (parsed.info && typeof parsed.info === 'object' && typeof parsed.info.schema === 'string' && parsed.info.schema.includes('postman')) {
      return null
    }
    const specVersion =
      typeof parsed.openapi === 'string'
        ? parsed.openapi
        : typeof parsed.swagger === 'string'
          ? parsed.swagger
          : null
    const isMaster = Boolean(specVersion)
    const isFragment = !isMaster && (Boolean(parsed.paths) || Boolean(parsed.components) || /\.openapi\.(?:ya?ml|json)$/i.test(lower))
    if (!isMaster && !isFragment) return null
    return {
      parsed,
      specVersion,
      isMaster,
      isFragment,
      format: lower.endsWith('.json') ? 'json' : lower.endsWith('.yml') ? 'yml' : 'yaml',
    }
  } catch {
    return null
  }
}

function findProjectRoot(startPath, explicitRoot) {
  if (explicitRoot) return path.resolve(explicitRoot)
  const resolved = path.resolve(startPath)
  let startDir = resolved
  try {
    if (fs.existsSync(resolved) && fs.statSync(resolved).isFile()) {
      startDir = path.dirname(resolved)
    } else if (!fs.existsSync(resolved)) {
      startDir = path.dirname(resolved)
    }
  } catch {
    startDir = path.dirname(resolved)
  }

  const tmpRoot = path.resolve(os.tmpdir()).toLowerCase()
  const homeRoot = path.resolve(os.homedir()).toLowerCase()
  const ancestors = []
  let curr = startDir
  for (let i = 0; i < 7; i++) {
    const lowerCurr = curr.toLowerCase()
    if (lowerCurr === tmpRoot || lowerCurr === homeRoot) break
    ancestors.push(curr)
    const parent = path.dirname(curr)
    if (parent === curr) break
    curr = parent
  }

  for (const dir of ancestors) {
    if (fs.existsSync(path.join(dir, '.git'))) return dir
  }
  for (const dir of ancestors) {
    try {
      const names = fs.readdirSync(dir)
      if (names.some((n) => ROOT_MANIFEST_FILES.has(n) || /\.sln$/i.test(n))) return dir
    } catch {
      // ignore unreadable parent
    }
  }
  let stripped = startDir
  for (let i = 0; i < 4; i++) {
    const base = path.basename(stripped).toLowerCase()
    const parent = path.dirname(stripped)
    if (parent === stripped) break
    const lowerParent = parent.toLowerCase()
    if (lowerParent === tmpRoot || lowerParent === homeRoot || path.dirname(parent) === parent) break
    if (!SPEC_CONTAINER_DIR_NAMES.has(base)) break
    stripped = parent
  }
  return stripped
}

function discoverProjectApiArtifacts(targetPathOrRoot, explicitRoot) {
  const projectRoot = findProjectRoot(targetPathOrRoot, explicitRoot)
  const openApiSpecs = []
  const modularFragments = []
  const collections = {
    bruno: [],
    postman: [],
    postmanEnvironments: [],
    insomnia: [],
    hoppscotch: [],
    thunderClient: [],
    httpFiles: [],
  }

  if (!fs.existsSync(projectRoot)) {
    return {
      projectRoot,
      openApiSpecs,
      modularFragments,
      openApiFolders: [],
      collections,
      detectedFormats: [],
      detectedCollectionFormat: 'none',
      primaryCollection: null,
    }
  }

  const queue = [{ dir: projectRoot, depth: 0 }]
  let scannedFiles = 0
  const MAX_DEPTH = 5
  const MAX_FILES = 2500

  while (queue.length > 0 && scannedFiles < MAX_FILES) {
    const { dir, depth } = queue.shift()
    let entries = []
    try {
      entries = fs.readdirSync(dir, { withFileTypes: true })
    } catch {
      continue
    }

    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name)
      const lower = entry.name.toLowerCase()

      if (entry.isDirectory()) {
        if (IGNORED_SCAN_DIRS.has(entry.name)) continue
        if (lower === '.insomnia') {
          collections.insomnia.push(fullPath)
          continue
        }
        if (lower === 'thunder-tests') {
          collections.thunderClient.push(fullPath)
          continue
        }
        if (entry.name.startsWith('.') && lower !== '.bruno' && lower !== '.vscode') continue
        if (depth < MAX_DEPTH) queue.push({ dir: fullPath, depth: depth + 1 })
        continue
      }

      if (!entry.isFile()) continue
      scannedFiles++

      if (lower === 'bruno.json' || (lower.endsWith('.bru') && path.basename(dir).toLowerCase() !== 'environments')) {
        if (lower === 'bruno.json') {
          collections.bruno.push({ type: 'bruno.json', root: dir, path: fullPath })
        } else if (!collections.bruno.some((b) => fullPath.startsWith(b.root + path.sep) || b.root === dir)) {
          collections.bruno.push({ type: '*.bru', root: dir, path: fullPath })
        }
        continue
      }
      if (/postman_collection\.json$/i.test(lower)) {
        collections.postman.push(fullPath)
        continue
      }
      if (/postman_environment\.json$/i.test(lower)) {
        collections.postmanEnvironments.push(fullPath)
        continue
      }
      if (/insomnia.*\.(?:json|ya?ml)$/i.test(lower)) {
        collections.insomnia.push(fullPath)
        continue
      }
      if (/hoppscotch.*\.json$/i.test(lower)) {
        collections.hoppscotch.push(fullPath)
        continue
      }
      if (/thundercollection.*\.json$/i.test(lower)) {
        collections.thunderClient.push(fullPath)
        continue
      }
      if (lower.endsWith('.http') || lower.endsWith('.rest')) {
        collections.httpFiles.push(fullPath)
        continue
      }

      const candidate = parseOpenApiCandidate(fullPath)
      if (!candidate) continue

      const rel = path.relative(projectRoot, fullPath).replace(/\\/g, '/')
      const parentName = path.basename(dir).toLowerCase()
      const inModularDir = MODULAR_SUBDIR_NAMES.includes(parentName) || parentName === 'components' || parentName === 'schemas'
      if (candidate.isMaster && !inModularDir) {
        const modFiles = listModuleSpecFiles(fullPath)
        openApiSpecs.push({
          path: fullPath,
          relativePath: rel,
          format: candidate.format,
          specVersion: candidate.specVersion,
          layoutMode: modFiles.length > 0 ? 'modular' : 'compact',
          moduleCount: modFiles.length,
        })
      } else {
        modularFragments.push({
          path: fullPath,
          relativePath: rel,
          format: candidate.format,
          isMasterHeader: candidate.isMaster,
        })
      }
    }
  }

  openApiSpecs.sort((a, b) => a.relativePath.localeCompare(b.relativePath))
  const folderSet = new Set([
    ...openApiSpecs.map((s) => path.dirname(s.path)),
    ...modularFragments.map((f) => path.dirname(f.path)),
  ])
  const openApiFolders = Array.from(folderSet).sort()

  const detectedFormats = []
  if (collections.bruno.length > 0) detectedFormats.push('bruno')
  if (collections.postman.length > 0) detectedFormats.push('postman')
  if (collections.insomnia.length > 0) detectedFormats.push('insomnia')
  if (collections.hoppscotch.length > 0) detectedFormats.push('hoppscotch')
  if (collections.thunderClient.length > 0) detectedFormats.push('thunder-client')
  if (collections.httpFiles.length > 0) detectedFormats.push('http-client')

  let detectedCollectionFormat = 'none'
  let primaryCollection = null
  if (detectedFormats.length === 1) {
    detectedCollectionFormat = detectedFormats[0]
  } else if (detectedFormats.length > 1) {
    detectedCollectionFormat = detectedFormats.includes('bruno') ? 'multiple_with_bruno' : 'multiple'
  }

  if (collections.bruno.length > 0) {
    const b = collections.bruno.find((x) => x.type === 'bruno.json') || collections.bruno[0]
    primaryCollection = { format: 'bruno', root: b.root, marker: path.relative(projectRoot, b.path).replace(/\\/g, '/') }
  } else if (collections.postman.length > 0) {
    const sortedPm = [...collections.postman].sort()
    const pmPath = sortedPm[0]
    const pmDir = path.dirname(pmPath)
    const matchingEnv = collections.postmanEnvironments.find((e) => path.dirname(e) === pmDir) || collections.postmanEnvironments[0] || null
    primaryCollection = {
      format: 'postman',
      root: pmDir,
      marker: path.relative(projectRoot, pmPath).replace(/\\/g, '/'),
      collectionPath: pmPath,
      environmentPath: matchingEnv,
    }
  } else if (collections.insomnia.length > 0) {
    primaryCollection = { format: 'insomnia', root: path.dirname(collections.insomnia[0]), marker: path.basename(collections.insomnia[0]) }
  } else if (collections.hoppscotch.length > 0) {
    primaryCollection = { format: 'hoppscotch', root: path.dirname(collections.hoppscotch[0]), marker: path.basename(collections.hoppscotch[0]) }
  } else if (collections.thunderClient.length > 0) {
    primaryCollection = { format: 'thunder-client', root: path.dirname(collections.thunderClient[0]), marker: path.basename(collections.thunderClient[0]) }
  } else if (collections.httpFiles.length > 0) {
    primaryCollection = { format: 'http-client', root: path.dirname(collections.httpFiles[0]), marker: path.basename(collections.httpFiles[0]) }
  }

  return {
    projectRoot,
    openApiSpecs,
    modularFragments,
    openApiFolders,
    collections,
    detectedFormats,
    detectedCollectionFormat,
    primaryCollection,
  }
}

function resolveTargetSpecPath(requestedSpecPath, options = {}) {
  const absRequested = path.resolve(requestedSpecPath)
  const artifacts = discoverProjectApiArtifacts(absRequested, options.projectRoot)
  if (fs.existsSync(absRequested)) {
    return {
      specPath: absRequested,
      requestedSpecPath: absRequested,
      resolvedFromExisting: false,
      artifacts,
    }
  }
  if (!options.allowNewSpec && artifacts.openApiSpecs.length === 1) {
    return {
      specPath: artifacts.openApiSpecs[0].path,
      requestedSpecPath: absRequested,
      resolvedFromExisting: true,
      artifacts,
    }
  }
  if (!options.allowNewSpec && artifacts.openApiSpecs.length > 1) {
    const listStr = artifacts.openApiSpecs.map((s) => s.relativePath).join(', ')
    throw new Error(
      `Multiple OpenAPI specs exist under ${artifacts.projectRoot} (${listStr}), and requested path ${requestedSpecPath} was not found. ` +
        'Pass the exact existing specPath you want to update (or allowNewSpec=true to create another spec).',
    )
  }
  if (options.mustExist) {
    throw new Error(`OpenAPI file not found at ${requestedSpecPath} (and none discovered under ${artifacts.projectRoot})`)
  }
  return {
    specPath: absRequested,
    requestedSpecPath: absRequested,
    resolvedFromExisting: false,
    artifacts,
  }
}

function loadOpenApiSpec(specPath, defaults = {}) {
  if (!fs.existsSync(specPath)) {
    return createEmptySpec(defaults)
  }
  const raw = fs.readFileSync(specPath, 'utf8')
  const parsed = isJsonPath(specPath) ? JSON.parse(raw) : YAML.parse(raw)
  return parsed || createEmptySpec(defaults)
}

function sortSpecDeterministically(spec) {
  const sortedPaths = {}
  const routeKeys = Object.keys(spec.paths || {}).sort((a, b) => a.localeCompare(b))
  const discoveredTags = new Set()

  for (const route of routeKeys) {
    const item = spec.paths[route] || {}
    const sortedItem = {}
    for (const m of METHOD_SORT_ORDER) {
      if (item[m]) {
        sortedItem[m] = item[m]
        for (const t of item[m].tags || []) discoveredTags.add(t)
      }
    }
    for (const [k, v] of Object.entries(item)) {
      if (!sortedItem[k]) sortedItem[k] = v
    }
    sortedPaths[route] = sortedItem
  }

  spec.paths = sortedPaths

  const existingTagMap = new Map()
  for (const t of spec.tags || []) {
    if (t && t.name) existingTagMap.set(t.name, t)
  }
  for (const tName of discoveredTags) {
    if (!existingTagMap.has(tName)) {
      existingTagMap.set(tName, {
        name: tName,
        description: `Endpoints for ${tName}`,
      })
    }
  }
  spec.tags = Array.from(existingTagMap.values()).sort((a, b) =>
    a.name.localeCompare(b.name),
  )
  return spec
}

function saveOpenApiSpec(specPath, spec) {
  sortSpecDeterministically(spec)
  fs.mkdirSync(path.dirname(specPath), { recursive: true })
  if (isJsonPath(specPath)) {
    fs.writeFileSync(specPath, JSON.stringify(spec, null, 2) + '\n', 'utf8')
  } else {
    fs.writeFileSync(specPath, YAML.stringify(spec, { indent: 2, lineWidth: 0 }), 'utf8')
  }
}

function getModulesDir(masterSpecPath) {
  const parent = path.dirname(masterSpecPath)
  for (const dirName of MODULAR_SUBDIR_NAMES) {
    const candidate = path.join(parent, dirName)
    if (fs.existsSync(candidate) && fs.statSync(candidate).isDirectory()) {
      const files = fs.readdirSync(candidate).filter((f) => /\.(?:ya?ml|json)$/i.test(f) && !f.startsWith('.'))
      if (files.length > 0) return candidate
    }
  }
  return path.join(parent, 'modules')
}

function listModuleSpecFiles(masterSpecPath) {
  const parent = path.dirname(masterSpecPath)
  const found = []
  for (const dirName of MODULAR_SUBDIR_NAMES) {
    const candidateDir = path.join(parent, dirName)
    if (!fs.existsSync(candidateDir) || !fs.statSync(candidateDir).isDirectory()) continue
    const files = fs
      .readdirSync(candidateDir)
      .filter((f) => {
        const lower = f.toLowerCase()
        if (lower.startsWith('.') || SKIP_SPEC_BASENAME_RE.test(lower)) return false
        return lower.endsWith('.yaml') || lower.endsWith('.yml') || lower.endsWith('.json')
      })
      .sort()
      .map((f) => path.join(candidateDir, f))
    found.push(...files)
  }
  return found
}

function detectModuleFilename(modulesDir, slug, masterSpecPath) {
  if (fs.existsSync(modulesDir)) {
    const files = fs.readdirSync(modulesDir).filter((f) => /\.(?:ya?ml|json)$/i.test(f))
    if (files.some((f) => f.toLowerCase().endsWith('.openapi.yml'))) return `${slug}.openapi.yml`
    if (files.some((f) => f.toLowerCase().endsWith('.openapi.json'))) return `${slug}.openapi.json`
    if (files.some((f) => f.toLowerCase().endsWith('.openapi.yaml'))) return `${slug}.openapi.yaml`
    if (files.some((f) => f.toLowerCase().endsWith('.yml'))) return `${slug}.yml`
    if (files.some((f) => f.toLowerCase().endsWith('.json'))) return `${slug}.json`
    if (files.some((f) => f.toLowerCase().endsWith('.yaml'))) return `${slug}.yaml`
  }
  const ext = getSpecExtension(masterSpecPath)
  return `${slug}.openapi${ext}`
}

function bundleModulesIntoMaster(masterSpecPath, defaults = {}) {
  const masterSpec = loadOpenApiSpec(masterSpecPath, defaults)
  const moduleFiles = listModuleSpecFiles(masterSpecPath)
  if (moduleFiles.length === 0) return masterSpec

  const mergedPaths = { ...(masterSpec.paths || {}) }
  const mergedComponents = { ...(masterSpec.components || {}) }
  const compBuckets = ['schemas', 'parameters', 'responses', 'requestBodies', 'headers', 'securitySchemes', 'examples']
  for (const bucket of compBuckets) {
    mergedComponents[bucket] = { ...(mergedComponents[bucket] || {}) }
  }

  for (const modFile of moduleFiles) {
    const modSpec = loadOpenApiSpec(modFile)
    for (const [routePath, pathItem] of Object.entries(modSpec.paths || {})) {
      if (mergedPaths[routePath] && typeof mergedPaths[routePath].$ref === 'string') continue
      if (!mergedPaths[routePath]) mergedPaths[routePath] = {}
      Object.assign(mergedPaths[routePath], pathItem)
    }
    if (modSpec.components) {
      for (const bucket of compBuckets) {
        if (modSpec.components[bucket]) {
          Object.assign(mergedComponents[bucket], modSpec.components[bucket])
        }
      }
    }
  }

  masterSpec.paths = mergedPaths
  masterSpec.components = mergedComponents
  saveOpenApiSpec(masterSpecPath, masterSpec)
  return masterSpec
}

function splitMasterIntoModules(masterSpecPath) {
  const masterSpec = loadOpenApiSpec(masterSpecPath)
  const modulesDir = getModulesDir(masterSpecPath)
  fs.mkdirSync(modulesDir, { recursive: true })

  const byModule = new Map()
  for (const [routePath, pathItem] of Object.entries(masterSpec.paths || {})) {
    for (const method of METHOD_SORT_ORDER) {
      const op = pathItem[method]
      if (!op) continue
      const primaryTag = (op.tags && op.tags[0]) || 'General'
      const topModule = primaryTag.split('/')[0].trim()
      const slug = sanitizeSlug(topModule)
      if (!byModule.has(slug)) {
        byModule.set(
          slug,
          createEmptySpec({
            title: `${(masterSpec.info && masterSpec.info.title) || 'API'} - ${topModule} Module`,
            serverUrl:
              masterSpec.servers && masterSpec.servers[0] && masterSpec.servers[0].url,
          }),
        )
      }
      const modSpec = byModule.get(slug)
      if (!modSpec.paths[routePath]) modSpec.paths[routePath] = {}
      modSpec.paths[routePath][method] = op
    }
  }

  const writtenFiles = []
  for (const [slug, modSpec] of byModule.entries()) {
    const modPath = path.join(modulesDir, detectModuleFilename(modulesDir, slug, masterSpecPath))
    saveOpenApiSpec(modPath, modSpec)
    writtenFiles.push(modPath)
  }
  return writtenFiles
}

function upsertOperationInSpec(spec, params) {
  if (!spec.paths) spec.paths = {}
  const routePath = params.routePath.startsWith('/') ? params.routePath : `/${params.routePath}`
  const method = params.method.toLowerCase()
  if (!spec.paths[routePath]) spec.paths[routePath] = {}

  const existing = spec.paths[routePath][method] || {}
  const parameters = []

  for (const p of params.pathParams || []) {
    parameters.push({
      name: p.name,
      in: 'path',
      required: true,
      description: p.description || `Path parameter ${p.name}`,
      schema: { type: p.type || 'string' },
      ...(p.example !== undefined ? { example: p.example } : {}),
    })
  }

  for (const q of params.queryParams || []) {
    parameters.push({
      name: q.name,
      in: 'query',
      required: Boolean(q.required),
      description: q.description || `Query parameter ${q.name}`,
      schema: { type: q.type || 'string' },
      ...(q.example !== undefined ? { example: q.example } : {}),
    })
  }

  const operation = {
    summary: params.summary || existing.summary || `${params.method.toUpperCase()} ${routePath}`,
    ...(params.description || existing.description
      ? { description: params.description || existing.description }
      : {}),
    tags: params.tags && params.tags.length > 0 ? params.tags : existing.tags || ['General'],
    operationId:
      existing.operationId ||
      `${method}_${routePath.replace(/[^a-zA-Z0-9]+/g, '_').replace(/^_|_$/g, '')}`,
  }

  if (params.requiresAuth) {
    if (!spec.components) spec.components = {}
    if (!spec.components.securitySchemes) {
      spec.components.securitySchemes = {
        BearerAuth: { type: 'http', scheme: 'bearer', bearerFormat: 'JWT' },
      }
    }
    operation.security = [{ BearerAuth: [] }]
  } else if (existing.security) {
    operation.security = existing.security
  }

  if (parameters.length > 0) {
    operation.parameters = parameters
  } else if (existing.parameters) {
    operation.parameters = existing.parameters
  }

  if (params.requestExample !== undefined || params.requestSchema !== undefined) {
    const schema = params.requestSchema || inferJsonSchema(params.requestExample)
    operation.requestBody = {
      required: true,
      content: {
        'application/json': {
          schema,
          ...(params.requestExample !== undefined ? { example: params.requestExample } : {}),
        },
      },
    }
  } else if (existing.requestBody) {
    operation.requestBody = existing.requestBody
  }

  const mergedResponses = { ...(existing.responses || {}) }
  if (params.responses) {
    for (const [statusCode, respDef] of Object.entries(params.responses)) {
      const hasBody = respDef.example !== undefined || respDef.schema !== undefined
      mergedResponses[String(statusCode)] = {
        description: respDef.description || `HTTP ${statusCode} response`,
        ...(hasBody
          ? {
              content: {
                'application/json': {
                  schema: respDef.schema || inferJsonSchema(respDef.example),
                  ...(respDef.example !== undefined ? { example: respDef.example } : {}),
                },
              },
            }
          : {}),
      }
    }
  }

  if (Object.keys(mergedResponses).length === 0) {
    mergedResponses['200'] = { description: 'Successful response' }
  }
  operation.responses = mergedResponses

  spec.paths[routePath][method] = operation
  return operation
}

function handleUpsertOpenApiEndpoint(args) {
  const resolution = resolveTargetSpecPath(args.specPath, {
    projectRoot: args.projectRoot,
    allowNewSpec: args.allowNewSpec,
  })
  const masterSpecPath = resolution.specPath
  const specExistedBefore = fs.existsSync(masterSpecPath)
  const existingModules = listModuleSpecFiles(masterSpecPath)
  const autoThreshold =
    args.autoModularThreshold !== undefined ? args.autoModularThreshold : 4

  const isAlreadyModular = Boolean(args.moduleName) || existingModules.length > 0

  if (isAlreadyModular) {
    const primaryTag = (args.tags && args.tags[0]) || 'General'
    const slug = sanitizeSlug(args.moduleName || primaryTag.split('/')[0])
    const modulesDir = getModulesDir(masterSpecPath)
    const moduleFilename = detectModuleFilename(modulesDir, slug, masterSpecPath)
    const moduleSpecPath = path.join(modulesDir, moduleFilename)

    if (existingModules.length === 0 && specExistedBefore) {
      splitMasterIntoModules(masterSpecPath)
    }

    const modSpec = loadOpenApiSpec(moduleSpecPath, {
      title: `${args.title || 'Project API'} - ${slug} Module`,
      serverUrl: args.serverUrl,
    })
    const operation = upsertOperationInSpec(modSpec, args)
    saveOpenApiSpec(moduleSpecPath, modSpec)

    bundleModulesIntoMaster(masterSpecPath, {
      title: args.title,
      serverUrl: args.serverUrl,
    })

    return {
      status: 'updated',
      layoutMode: 'modular',
      masterSpecPath,
      moduleSpecPath,
      ...(resolution.resolvedFromExisting
        ? { resolvedFromExisting: true, requestedSpecPath: resolution.requestedSpecPath }
        : {}),
      routePath: args.routePath,
      method: args.method.toUpperCase(),
      operationId: operation.operationId,
      tags: operation.tags,
    }
  }

  // Compact mode first; never split an already-existing brownfield single-file spec unless allowAutoSplit=true
  const spec = loadOpenApiSpec(masterSpecPath, {
    title: args.title,
    serverUrl: args.serverUrl,
  })
  const operation = upsertOperationInSpec(spec, args)
  saveOpenApiSpec(masterSpecPath, spec)

  if (
    autoThreshold > 0 &&
    (spec.tags || []).length > autoThreshold &&
    (!specExistedBefore || args.allowAutoSplit === true)
  ) {
    const moduleFiles = splitMasterIntoModules(masterSpecPath)
    bundleModulesIntoMaster(masterSpecPath, {
      title: args.title,
      serverUrl: args.serverUrl,
    })
    return {
      status: 'updated_and_promoted_to_modular',
      layoutMode: 'modular',
      masterSpecPath,
      ...(resolution.resolvedFromExisting
        ? { resolvedFromExisting: true, requestedSpecPath: resolution.requestedSpecPath }
        : {}),
      moduleFilesCreated: moduleFiles.length,
      routePath: args.routePath,
      method: args.method.toUpperCase(),
      operationId: operation.operationId,
      tags: operation.tags,
    }
  }

  return {
    status: 'updated',
    layoutMode: 'compact',
    specPath: masterSpecPath,
    ...(resolution.resolvedFromExisting
      ? { resolvedFromExisting: true, requestedSpecPath: resolution.requestedSpecPath }
      : {}),
    routePath: args.routePath,
    method: args.method.toUpperCase(),
    operationId: operation.operationId,
    tags: operation.tags,
  }
}

function handleBulkUpsertOpenApiEndpoints(args) {
  const resolution = resolveTargetSpecPath(args.specPath, {
    projectRoot: args.projectRoot,
    allowNewSpec: args.allowNewSpec,
  })
  const resolvedSpecPath = resolution.specPath
  const endpoints = args.endpoints || []
  const results = []
  for (const ep of endpoints) {
    const res = handleUpsertOpenApiEndpoint({
      ...ep,
      specPath: resolvedSpecPath,
      projectRoot: args.projectRoot,
      allowNewSpec: true,
      allowAutoSplit: args.allowAutoSplit,
      title: args.title,
      serverUrl: args.serverUrl,
      autoModularThreshold: args.autoModularThreshold,
    })
    results.push({
      method: res.method,
      routePath: res.routePath,
      layoutMode: res.layoutMode,
    })
  }

  // Collection format: auto (default) discovers all collections across the project and avoids imposing Postman.
  const requestedFormat = args.collectionFormat || (args.autoSyncPostman === false ? 'none' : 'auto')
  const detected = detectApiCollectionFormat(resolvedSpecPath, args.projectRoot)
  const effectiveFormat = requestedFormat === 'auto' ? detected.format : requestedFormat
  let postmanResult = null
  let collectionNote = null
  if (endpoints.length > 0) {
    if (effectiveFormat === 'postman') {
      postmanResult = handleSyncPostmanCollection({
        specPath: resolvedSpecPath,
        projectRoot: args.projectRoot,
        baseUrl: args.serverUrl,
        force: requestedFormat === 'postman',
      })
    } else if (effectiveFormat === 'bruno') {
      collectionNote = `Bruno detected (${detected.marker} at ${detected.root}); no Postman files generated. Add/update .bru requests following the existing collection's structure, naming, and environments.`
    } else if (effectiveFormat === 'multiple' || effectiveFormat === 'multiple_with_bruno') {
      collectionNote = `Multiple API client formats detected (${detected.detectedFormats.join(', ')}); skipped automatic Postman write to avoid overwriting/conflicting with existing collections.`
    } else if (effectiveFormat === 'none' && requestedFormat === 'auto') {
      collectionNote = 'No existing API client collection detected; generated OpenAPI only. Ask the Monarch which format to use (Bruno/Postman) or pass collectionFormat explicitly.'
    } else if (effectiveFormat === 'none') {
      collectionNote = 'collectionFormat=none; OpenAPI only.'
    } else {
      collectionNote = `Detected ${effectiveFormat} (${detected.marker || ''}); no automatic collection generator available. Update the existing collection manually.`
    }
  }

  const validation = handleValidateOpenApiSpec({ specPath: resolvedSpecPath, projectRoot: args.projectRoot })
  return {
    status: 'bulk_updated',
    totalUpserted: results.length,
    layoutMode: validation.layoutMode,
    modules: validation.modules,
    masterSpecPath: resolvedSpecPath,
    ...(resolution.resolvedFromExisting
      ? { resolvedFromExisting: true, requestedSpecPath: resolution.requestedSpecPath }
      : {}),
    detectedCollectionFormat: detected.format,
    detectedCollectionFormats: detected.detectedFormats,
    effectiveCollectionFormat: effectiveFormat,
    ...(collectionNote ? { collectionNote } : {}),
    ...(postmanResult
      ? {
          postmanCollectionPath: postmanResult.collectionPath,
          postmanEnvironmentPath: postmanResult.environmentPath,
        }
      : {}),
  }
}

async function handleTestApiEndpoint(args) {
  const urlObj = new URL(args.url)
  if (args.queryParams) {
    for (const [k, v] of Object.entries(args.queryParams)) {
      urlObj.searchParams.set(k, String(v))
    }
  }

  const headers = { ...(args.headers || {}) }
  if (args.bearerToken) {
    headers['Authorization'] = `Bearer ${args.bearerToken}`
  }

  let requestBodyString
  if (args.body !== undefined && args.method !== 'GET' && args.method !== 'HEAD') {
    if (typeof args.body === 'string') {
      requestBodyString = args.body
    } else {
      requestBodyString = JSON.stringify(args.body)
      if (!headers['Content-Type'] && !headers['content-type']) {
        headers['Content-Type'] = 'application/json'
      }
    }
  }

  const timeoutMs = args.timeoutMs || 15000
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  const startedAt = performance.now()

  try {
    const response = await fetch(urlObj.toString(), {
      method: args.method,
      headers,
      body: requestBodyString,
      signal: controller.signal,
    })
    clearTimeout(timer)
    const durationMs = Math.round(performance.now() - startedAt)
    const rawText = await response.text()
    let parsedBody = rawText
    try {
      parsedBody = JSON.parse(rawText)
    } catch {
      // Keep raw text if not JSON
    }

    const responseHeaders = {}
    response.headers.forEach((value, key) => {
      responseHeaders[key] = value
    })

    const assertionPassed =
      args.expectedStatus !== undefined ? response.status === args.expectedStatus : response.ok

    let openApiRecorded = null
    if (args.recordToOpenApiPath) {
      const routePath = args.routePattern || urlObj.pathname
      const queryParamsList = []
      urlObj.searchParams.forEach((val, key) => {
        queryParamsList.push({ name: key, type: 'string', example: val })
      })
      openApiRecorded = handleUpsertOpenApiEndpoint({
        specPath: args.recordToOpenApiPath,
        moduleName: args.moduleName,
        serverUrl: `${urlObj.protocol}//${urlObj.host}`,
        routePath,
        method: args.method,
        summary: args.summary || `${args.method} ${routePath}`,
        tags: args.tag ? [args.tag] : undefined,
        requiresAuth: Boolean(args.bearerToken || headers['Authorization']),
        queryParams: queryParamsList,
        requestExample: typeof args.body === 'object' ? args.body : undefined,
        responses: {
          [String(response.status)]: {
            description: response.statusText || `HTTP ${response.status}`,
            example: typeof parsedBody === 'object' ? parsedBody : undefined,
          },
        },
      })
    }

    return {
      request: {
        method: args.method,
        url: urlObj.toString(),
      },
      response: {
        status: response.status,
        statusText: response.statusText,
        ok: response.ok,
        durationMs,
        headers: responseHeaders,
        body: parsedBody,
      },
      assertionPassed,
      ...(openApiRecorded ? { openApiRecorded } : {}),
    }
  } catch (err) {
    clearTimeout(timer)
    const durationMs = Math.round(performance.now() - startedAt)
    return {
      request: {
        method: args.method,
        url: urlObj.toString(),
      },
      error: err instanceof Error ? err.message : String(err),
      durationMs,
      assertionPassed: false,
    }
  }
}

function insertIntoFolderTree(rootItems, folderSegments, requestItem) {
  let currentLevel = rootItems
  for (const rawSeg of folderSegments) {
    const folderName = rawSeg.trim() || 'General'
    let folder = currentLevel.find(
      (entry) => Array.isArray(entry.item) && entry.name === folderName,
    )
    if (!folder) {
      folder = { name: folderName, item: [] }
      currentLevel.push(folder)
    }
    currentLevel = folder.item
  }
  currentLevel.push(requestItem)
}

function buildPostmanItem(routePath, method, op) {
  const postmanPathSegments = routePath
    .split('/')
    .filter(Boolean)
    .map((seg) => seg.replace(/^\{(.+)\}$/, ':$1'))

  const pathVariables = []
  const queryVariables = []
  for (const param of op.parameters || []) {
    if (param.in === 'path') {
      pathVariables.push({
        key: param.name,
        value: param.example !== undefined ? String(param.example) : `sample_${param.name}`,
        description: param.description || '',
      })
    } else if (param.in === 'query') {
      queryVariables.push({
        key: param.name,
        value: param.example !== undefined ? String(param.example) : '',
        description: param.description || '',
        disabled: !param.required && param.example === undefined,
      })
    }
  }

  const headers = [{ key: 'Accept', value: 'application/json' }]
  let bodyObj
  const jsonReqContent =
    op.requestBody && op.requestBody.content && op.requestBody.content['application/json']
  if (jsonReqContent) {
    headers.push({ key: 'Content-Type', value: 'application/json' })
    const ex =
      jsonReqContent.example !== undefined
        ? jsonReqContent.example
        : buildSampleFromSchema(jsonReqContent.schema)
    bodyObj = {
      mode: 'raw',
      raw: JSON.stringify(ex ?? {}, null, 2),
      options: { raw: { language: 'json' } },
    }
  }

  const requiresBearer = Array.isArray(op.security) && op.security.length > 0

  const savedResponses = []
  for (const [statusCode, respObj] of Object.entries(op.responses || {})) {
    const jsonResp = respObj && respObj.content && respObj.content['application/json']
    if (jsonResp && jsonResp.example !== undefined) {
      savedResponses.push({
        name: `${statusCode} - ${respObj.description || 'Response'}`,
        status: respObj.description || 'OK',
        code: Number(statusCode) || 200,
        _postman_previewlanguage: 'json',
        header: [{ key: 'Content-Type', value: 'application/json' }],
        body: JSON.stringify(jsonResp.example, null, 2),
      })
    }
  }

  return {
    name: `[${method.toUpperCase()}] ${op.summary || routePath}`,
    request: {
      method: method.toUpperCase(),
      header: headers,
      ...(requiresBearer
        ? {
            auth: {
              type: 'bearer',
              bearer: [{ key: 'token', value: '{{bearerToken}}', type: 'string' }],
            },
          }
        : {}),
      ...(bodyObj ? { body: bodyObj } : {}),
      url: {
        raw: `{{baseUrl}}/${postmanPathSegments.join('/')}`,
        host: ['{{baseUrl}}'],
        path: postmanPathSegments,
        ...(queryVariables.length > 0 ? { query: queryVariables } : {}),
        ...(pathVariables.length > 0 ? { variable: pathVariables } : {}),
      },
      description: op.description || op.summary || '',
    },
    response: savedResponses,
  }
}

/**
 * Detects the API client collection format already used by the project so generated artifacts
 * follow the existing convention (Bruno / Postman) instead of imposing Postman.
 * Walks up from the spec directory (max 6 levels) and stops at the first directory with a marker.
 */
function detectApiCollectionFormat(specPath, explicitRoot) {
  const artifacts = discoverProjectApiArtifacts(specPath, explicitRoot)
  const primary = artifacts.primaryCollection
  return {
    format: artifacts.detectedCollectionFormat,
    detectedFormats: artifacts.detectedFormats,
    root: primary ? primary.root : null,
    marker: primary ? primary.marker : null,
    primaryCollection: primary,
    artifacts,
  }
}

function handleDiscoverApiArtifacts(args) {
  return discoverProjectApiArtifacts(args.projectRoot, args.projectRoot)
}

function handleSyncPostmanCollection(args) {
  const resolution = resolveTargetSpecPath(args.specPath, {
    mustExist: true,
    projectRoot: args.projectRoot,
  })
  const resolvedSpecPath = resolution.specPath
  const detected = detectApiCollectionFormat(resolvedSpecPath, args.projectRoot)

  if (args.force !== true) {
    if (detected.format !== 'postman' && detected.format !== 'none') {
      throw new Error(
        `Existing project uses ${detected.format} (${detected.marker} at ${detected.root}). Refusing to create Postman files; ` +
          'author/update requests in the existing format, or pass force=true only if the Monarch explicitly requested Postman.',
      )
    }
  }

  const moduleFiles = listModuleSpecFiles(resolvedSpecPath)
  const isModular = moduleFiles.length > 0
  if (isModular) {
    bundleModulesIntoMaster(resolvedSpecPath)
  }

  const spec = loadOpenApiSpec(resolvedSpecPath)
  sortSpecDeterministically(spec)

  const baseUrl =
    args.baseUrl ||
    (spec.servers && spec.servers[0] && spec.servers[0].url) ||
    'http://localhost:3000'

  const rootItems = []
  let totalRequests = 0

  for (const [routePath, pathItem] of Object.entries(spec.paths || {})) {
    for (const method of METHOD_SORT_ORDER) {
      const op = pathItem[method]
      if (!op) continue
      const rawTag = (op.tags && op.tags[0]) || 'General'
      const folderSegments = rawTag.split('/').map((s) => s.trim()).filter(Boolean)
      const reqItem = buildPostmanItem(routePath, method, op)
      insertIntoFolderTree(rootItems, folderSegments, reqItem)
      totalRequests++
    }
  }

  const collection = {
    info: {
      name: (spec.info && spec.info.title) || 'Project API Collection',
      description:
        (spec.info && spec.info.description) ||
        'Generated from OpenAPI specification by Shadow Army.',
      schema: 'https://schema.getpostman.com/json/collection/v2.1.0/collection.json',
    },
    variable: [
      { key: 'baseUrl', value: baseUrl, type: 'string' },
      { key: 'bearerToken', value: '', type: 'string' },
    ],
    item: rootItems,
  }

  const specDir = path.dirname(resolvedSpecPath)
  const existingPm =
    detected.primaryCollection && detected.primaryCollection.format === 'postman'
      ? detected.primaryCollection
      : null
  const defaultOutDir = isModular ? path.join(specDir, 'postman') : specDir
  const collectionPath =
    args.collectionOutputPath ||
    (existingPm && existingPm.collectionPath) ||
    path.join(defaultOutDir, 'postman_collection.json')
  const envPath =
    args.environmentOutputPath ||
    (existingPm && existingPm.environmentPath) ||
    path.join(path.dirname(collectionPath), 'postman_environment.json')

  fs.mkdirSync(path.dirname(collectionPath), { recursive: true })
  fs.writeFileSync(collectionPath, JSON.stringify(collection, null, 2) + '\n', 'utf8')

  const environment = {
    name: `${(spec.info && spec.info.title) || 'Project API'} - Local Environment`,
    values: [
      { key: 'baseUrl', value: baseUrl, type: 'default', enabled: true },
      { key: 'bearerToken', value: '', type: 'secret', enabled: true },
    ],
    _postman_variable_scope: 'environment',
  }
  fs.mkdirSync(path.dirname(envPath), { recursive: true })
  fs.writeFileSync(envPath, JSON.stringify(environment, null, 2) + '\n', 'utf8')

  return {
    status: 'synced',
    layoutMode: isModular ? 'modular' : 'compact',
    specPath: resolvedSpecPath,
    collectionPath,
    environmentPath: envPath,
    topLevelFolders: rootItems.map((i) => i.name),
    totalRequests,
  }
}

function buildSampleFromSchema(schema) {
  if (!schema || typeof schema !== 'object') return {}
  if (schema.example !== undefined) return schema.example
  if (schema.type === 'string') return 'string'
  if (schema.type === 'integer' || schema.type === 'number') return 0
  if (schema.type === 'boolean') return true
  if (schema.type === 'array') {
    return [buildSampleFromSchema(schema.items)]
  }
  if (schema.type === 'object' || schema.properties) {
    const out = {}
    for (const [k, v] of Object.entries(schema.properties || {})) {
      out[k] = buildSampleFromSchema(v)
    }
    return out
  }
  return {}
}

function handleValidateOpenApiSpec(args) {
  const resolution = resolveTargetSpecPath(args.specPath, {
    mustExist: true,
    projectRoot: args.projectRoot,
  })
  const resolvedSpecPath = resolution.specPath
  const moduleFiles = listModuleSpecFiles(resolvedSpecPath)
  if (moduleFiles.length > 0) {
    bundleModulesIntoMaster(resolvedSpecPath)
  }

  const spec = loadOpenApiSpec(resolvedSpecPath)
  const issues = []
  const endpoints = []

  const specVersion = spec.openapi || spec.swagger
  if (!specVersion || (!String(spec.openapi || '').startsWith('3.') && String(spec.swagger || '') !== '2.0')) {
    issues.push('Missing or unsupported `openapi` (3.x) / `swagger` (2.0) version field.')
  }
  if (!spec.info || !spec.info.title || !spec.info.version) {
    issues.push('Missing `info.title` or `info.version`.')
  }

  for (const [routePath, pathItem] of Object.entries(spec.paths || {})) {
    for (const method of METHOD_SORT_ORDER) {
      const op = pathItem[method]
      if (!op) continue
      endpoints.push({
        method: method.toUpperCase(),
        path: routePath,
        summary: op.summary || '(missing summary)',
        tags: op.tags || [],
        responseCodes: Object.keys(op.responses || {}),
      })
      if (!op.summary) {
        issues.push(`${method.toUpperCase()} ${routePath}: missing summary`)
      }
      if (!op.responses || Object.keys(op.responses).length === 0) {
        issues.push(`${method.toUpperCase()} ${routePath}: missing responses object`)
      }
    }
  }

  return {
    valid: issues.length === 0,
    layoutMode: moduleFiles.length > 0 ? 'modular' : 'compact',
    modulesDir: moduleFiles.length > 0 ? path.dirname(moduleFiles[0]) : null,
    modules: moduleFiles.map((f) => path.basename(f)),
    specPath: resolvedSpecPath,
    ...(resolution.resolvedFromExisting
      ? { resolvedFromExisting: true, requestedSpecPath: resolution.requestedSpecPath }
      : {}),
    openapiVersion: specVersion,
    title: spec.info && spec.info.title,
    totalPaths: Object.keys(spec.paths || {}).length,
    totalOperations: endpoints.length,
    issues,
    endpoints,
  }
}

async function handleRunApiCollection(args) {
  const resolution = resolveTargetSpecPath(args.specPath, {
    mustExist: true,
    projectRoot: args.projectRoot,
  })
  const resolvedSpecPath = resolution.specPath
  const spec = loadOpenApiSpec(resolvedSpecPath)
  const moduleFiles = listModuleSpecFiles(resolvedSpecPath)
  const effectivePaths = { ...(spec.paths || {}) }
  for (const modFile of moduleFiles) {
    const modSpec = loadOpenApiSpec(modFile)
    for (const [rPath, pItem] of Object.entries(modSpec.paths || {})) {
      if (!effectivePaths[rPath] || typeof effectivePaths[rPath].$ref === 'string') {
        effectivePaths[rPath] = pItem
      } else {
        Object.assign(effectivePaths[rPath], pItem)
      }
    }
  }
  const baseUrl = args.baseUrl.replace(/\/+$/, '')
  const httpMethods = args.onlyGetRequests
    ? ['get']
    : ['get', 'post', 'put', 'patch', 'delete']

  const results = []
  for (const [routePath, pathItem] of Object.entries(effectivePaths)) {
    for (const method of httpMethods) {
      const op = pathItem[method]
      if (!op) continue
      if (
        args.tagFilter &&
        !(op.tags || []).some(
          (t) => t === args.tagFilter || t.startsWith(`${args.tagFilter}/`),
        )
      ) {
        continue
      }

      let resolvedPath = routePath
      const queryParams = {}
      for (const param of op.parameters || []) {
        if (param.in === 'path') {
          const val = param.example !== undefined ? String(param.example) : '1'
          resolvedPath = resolvedPath.replace(`{${param.name}}`, encodeURIComponent(val))
        } else if (param.in === 'query' && param.example !== undefined) {
          queryParams[param.name] = String(param.example)
        }
      }

      const jsonReqContent =
        op.requestBody &&
        op.requestBody.content &&
        op.requestBody.content['application/json']
      const reqBody = jsonReqContent
        ? jsonReqContent.example ?? buildSampleFromSchema(jsonReqContent.schema)
        : undefined

      const res = await handleTestApiEndpoint({
        url: `${baseUrl}${resolvedPath}`,
        method: method.toUpperCase(),
        queryParams,
        bearerToken: args.bearerToken,
        body: reqBody,
        timeoutMs: 10000,
      })

      results.push({
        endpoint: `${method.toUpperCase()} ${routePath}`,
        url: res.request.url,
        status: res.response ? res.response.status : 'ERROR',
        ok: res.response ? res.response.ok : false,
        durationMs: res.response ? res.response.durationMs : res.durationMs,
        error: res.error || null,
      })
    }
  }

  const passed = results.filter((r) => r.ok).length
  return {
    baseUrl,
    totalExecuted: results.length,
    passed,
    failed: results.length - passed,
    results,
  }
}

function sendJsonRpc(payload) {
  process.stdout.write(JSON.stringify(payload) + '\n')
}

function sendResult(id, result) {
  sendJsonRpc({ jsonrpc: '2.0', id, result })
}

function sendToolText(id, data, isError = false) {
  sendResult(id, {
    content: [
      {
        type: 'text',
        text: typeof data === 'string' ? data : JSON.stringify(data, null, 2),
      },
    ],
    isError,
  })
}

const rl = readline.createInterface({
  input: process.stdin,
  terminal: false,
})

rl.on('line', async (line) => {
  const trimmed = line.trim()
  if (!trimmed) return

  let msg
  try {
    msg = JSON.parse(trimmed)
  } catch {
    return
  }

  const { id, method, params } = msg

  if (method === 'initialize') {
    sendResult(id, {
      protocolVersion: PROTOCOL_VERSION,
      capabilities: { tools: {} },
      serverInfo: SERVER_INFO,
    })
    return
  }

  if (method === 'notifications/initialized') {
    return
  }

  if (method === 'ping') {
    sendResult(id, {})
    return
  }

  if (method === 'tools/list') {
    sendResult(id, { tools: TOOLS })
    return
  }

  if (method === 'tools/call') {
    const toolName = params && params.name
    const toolArgs = (params && params.arguments) || {}
    try {
      if (toolName === 'discover_api_artifacts') {
        const out = handleDiscoverApiArtifacts(toolArgs)
        sendToolText(id, out)
      } else if (toolName === 'test_api_endpoint') {
        const out = await handleTestApiEndpoint(toolArgs)
        sendToolText(id, out)
      } else if (toolName === 'upsert_openapi_endpoint') {
        const out = handleUpsertOpenApiEndpoint(toolArgs)
        sendToolText(id, out)
      } else if (toolName === 'bulk_upsert_openapi_endpoints') {
        const out = handleBulkUpsertOpenApiEndpoints(toolArgs)
        sendToolText(id, out)
      } else if (toolName === 'sync_postman_collection') {
        const out = handleSyncPostmanCollection(toolArgs)
        sendToolText(id, out)
      } else if (toolName === 'validate_openapi_spec') {
        const out = handleValidateOpenApiSpec(toolArgs)
        sendToolText(id, out)
      } else if (toolName === 'run_api_collection') {
        const out = await handleRunApiCollection(toolArgs)
        sendToolText(id, out)
      } else {
        sendToolText(id, `Unknown tool: ${toolName}`, true)
      }
    } catch (error) {
      sendToolText(
        id,
        `Error in ${toolName}: ${error instanceof Error ? error.message : String(error)}`,
        true,
      )
    }
    return
  }

  if (id !== undefined && id !== null) {
    sendResult(id, {})
  }
})
