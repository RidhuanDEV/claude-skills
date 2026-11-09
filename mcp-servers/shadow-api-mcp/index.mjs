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
import path from 'node:path'
import readline from 'node:readline'
import YAML from 'yaml'

const PROTOCOL_VERSION = '2024-11-05'
const SERVER_INFO = {
  name: 'shadow-api-mcp',
  version: '1.1.0',
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
    name: 'upsert_openapi_endpoint',
    description:
      'Create or update an endpoint definition in a project OpenAPI 3.1.0 specification. Supports both Compact Mode (single docs/api/openapi.yaml for small projects) and Modular Mode (docs/api/modules/<moduleName>.openapi.yaml + auto-bundled master docs/api/openapi.yaml for multi-module projects).',
    inputSchema: {
      type: 'object',
      properties: {
        specPath: {
          type: 'string',
          description:
            'Absolute path to the master openapi.yaml (recommended: <project>/docs/api/openapi.yaml)',
        },
        moduleName: {
          type: 'string',
          description:
            'Optional module slug for large/multi-module projects (e.g. "auth", "users", "inventory"). Writes the endpoint into docs/api/modules/<moduleName>.openapi.yaml and bundles all modules into master specPath.',
        },
        autoModularThreshold: {
          type: 'number',
          description:
            'Automatically split into docs/api/modules/<tag>.openapi.yaml when total tags exceed this count (default: 4). Set 0 to disable auto-splitting.',
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
      'Batch-create or update multiple endpoints at once in OpenAPI 3.1.0 (ideal for generating OpenAPI + Postman collections from an existing backend codebase in a single call). Automatically uses Modular Mode (docs/api/modules/<module>.openapi.yaml + master bundle) when modules/tags exceed threshold, and optionally syncs Postman collection immediately.',
    inputSchema: {
      type: 'object',
      properties: {
        specPath: {
          type: 'string',
          description: 'Absolute path to master openapi.yaml (e.g. <project>/docs/api/openapi.yaml)',
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
          description: 'If true (default), automatically generates/updates postman_collection.json and postman_environment.json after upserting all endpoints',
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
      'Generate or update a neatly structured Postman Collection v2.1.0 (postman_collection.json) and Postman Environment (postman_environment.json) from OpenAPI 3.1/3.0. Supports nested folder hierarchies (via tag paths like "Module/Submodule"), sorted HTTP methods, {{baseUrl}} and {{bearerToken}} variables, and per-module Postman collections when docs/api/modules/ exists.',
    inputSchema: {
      type: 'object',
      properties: {
        specPath: {
          type: 'string',
          description: 'Absolute path to master openapi.yaml or openapi.json',
        },
        collectionOutputPath: {
          type: 'string',
          description:
            'Optional output path for postman_collection.json (defaults to docs/api/postman/postman_collection.json when modular, or next to specPath when compact)',
        },
        environmentOutputPath: {
          type: 'string',
          description: 'Optional output path for postman_environment.json',
        },
        baseUrl: {
          type: 'string',
          description: 'Default baseUrl variable value (e.g. http://localhost:3000)',
        },
      },
      required: ['specPath'],
    },
  },
  {
    name: 'validate_openapi_spec',
    description:
      'Validate and audit an OpenAPI specification (and any modular files under docs/api/modules/), reporting layout mode (compact vs modular), modules, version, total paths/operations, and any missing summaries or response definitions.',
    inputSchema: {
      type: 'object',
      properties: {
        specPath: {
          type: 'string',
          description: 'Absolute path to master openapi.yaml or openapi.json',
        },
      },
      required: ['specPath'],
    },
  },
  {
    name: 'run_api_collection',
    description:
      'Run automated live HTTP smoke tests for all (or tag/module-filtered) endpoints defined in an openapi.yaml / openapi.json file against a target baseUrl.',
    inputSchema: {
      type: 'object',
      properties: {
        specPath: {
          type: 'string',
          description: 'Absolute path to master openapi.yaml or openapi.json',
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

function loadOpenApiSpec(specPath, defaults = {}) {
  if (!fs.existsSync(specPath)) {
    return createEmptySpec(defaults)
  }
  const raw = fs.readFileSync(specPath, 'utf8')
  const parsed = specPath.endsWith('.json') ? JSON.parse(raw) : YAML.parse(raw)
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
  if (specPath.endsWith('.json')) {
    fs.writeFileSync(specPath, JSON.stringify(spec, null, 2) + '\n', 'utf8')
  } else {
    fs.writeFileSync(specPath, YAML.stringify(spec, { indent: 2, lineWidth: 0 }), 'utf8')
  }
}

function getModulesDir(masterSpecPath) {
  return path.join(path.dirname(masterSpecPath), 'modules')
}

function listModuleSpecFiles(masterSpecPath) {
  const modulesDir = getModulesDir(masterSpecPath)
  if (!fs.existsSync(modulesDir)) return []
  return fs
    .readdirSync(modulesDir)
    .filter((f) => f.endsWith('.openapi.yaml') || f.endsWith('.openapi.json'))
    .sort()
    .map((f) => path.join(modulesDir, f))
}

function bundleModulesIntoMaster(masterSpecPath, defaults = {}) {
  const masterSpec = loadOpenApiSpec(masterSpecPath, defaults)
  const moduleFiles = listModuleSpecFiles(masterSpecPath)
  if (moduleFiles.length === 0) return masterSpec

  const mergedPaths = {}
  const mergedSchemas = { ...((masterSpec.components && masterSpec.components.schemas) || {}) }

  for (const modFile of moduleFiles) {
    const modSpec = loadOpenApiSpec(modFile)
    for (const [routePath, pathItem] of Object.entries(modSpec.paths || {})) {
      if (!mergedPaths[routePath]) mergedPaths[routePath] = {}
      Object.assign(mergedPaths[routePath], pathItem)
    }
    if (modSpec.components && modSpec.components.schemas) {
      Object.assign(mergedSchemas, modSpec.components.schemas)
    }
  }

  masterSpec.paths = mergedPaths
  if (!masterSpec.components) masterSpec.components = {}
  masterSpec.components.schemas = mergedSchemas
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
    const modPath = path.join(modulesDir, `${slug}.openapi.yaml`)
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
  const masterSpecPath = args.specPath
  const existingModules = listModuleSpecFiles(masterSpecPath)
  const autoThreshold =
    args.autoModularThreshold !== undefined ? args.autoModularThreshold : 4

  const isAlreadyModular = Boolean(args.moduleName) || existingModules.length > 0

  if (isAlreadyModular) {
    const primaryTag = (args.tags && args.tags[0]) || 'General'
    const slug = sanitizeSlug(args.moduleName || primaryTag.split('/')[0])
    const moduleSpecPath = path.join(getModulesDir(masterSpecPath), `${slug}.openapi.yaml`)

    if (existingModules.length === 0 && fs.existsSync(masterSpecPath)) {
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
      routePath: args.routePath,
      method: args.method.toUpperCase(),
      operationId: operation.operationId,
      tags: operation.tags,
    }
  }

  // Compact mode first
  const spec = loadOpenApiSpec(masterSpecPath, {
    title: args.title,
    serverUrl: args.serverUrl,
  })
  const operation = upsertOperationInSpec(spec, args)
  saveOpenApiSpec(masterSpecPath, spec)

  // Check if project has grown past the autoModularThreshold
  if (autoThreshold > 0 && (spec.tags || []).length > autoThreshold) {
    const moduleFiles = splitMasterIntoModules(masterSpecPath)
    bundleModulesIntoMaster(masterSpecPath, {
      title: args.title,
      serverUrl: args.serverUrl,
    })
    return {
      status: 'updated_and_promoted_to_modular',
      layoutMode: 'modular',
      masterSpecPath,
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
    routePath: args.routePath,
    method: args.method.toUpperCase(),
    operationId: operation.operationId,
    tags: operation.tags,
  }
}

function handleBulkUpsertOpenApiEndpoints(args) {
  const endpoints = args.endpoints || []
  const results = []
  for (const ep of endpoints) {
    const res = handleUpsertOpenApiEndpoint({
      ...ep,
      specPath: args.specPath,
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

  let postmanResult = null
  if (args.autoSyncPostman !== false && endpoints.length > 0) {
    postmanResult = handleSyncPostmanCollection({
      specPath: args.specPath,
      baseUrl: args.serverUrl,
    })
  }

  const validation = handleValidateOpenApiSpec({ specPath: args.specPath })
  return {
    status: 'bulk_updated',
    totalUpserted: results.length,
    layoutMode: validation.layoutMode,
    modules: validation.modules,
    masterSpecPath: args.specPath,
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

function handleSyncPostmanCollection(args) {
  if (!fs.existsSync(args.specPath)) {
    throw new Error(`OpenAPI file not found at ${args.specPath}`)
  }

  const moduleFiles = listModuleSpecFiles(args.specPath)
  const isModular = moduleFiles.length > 0
  if (isModular) {
    bundleModulesIntoMaster(args.specPath)
  }

  const spec = loadOpenApiSpec(args.specPath)
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

  const specDir = path.dirname(args.specPath)
  const defaultOutDir = isModular ? path.join(specDir, 'postman') : specDir
  const collectionPath =
    args.collectionOutputPath || path.join(defaultOutDir, 'postman_collection.json')
  const envPath =
    args.environmentOutputPath || path.join(defaultOutDir, 'postman_environment.json')

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
  if (!fs.existsSync(args.specPath)) {
    throw new Error(`OpenAPI file not found at ${args.specPath}`)
  }
  const moduleFiles = listModuleSpecFiles(args.specPath)
  if (moduleFiles.length > 0) {
    bundleModulesIntoMaster(args.specPath)
  }

  const spec = loadOpenApiSpec(args.specPath)
  const issues = []
  const endpoints = []

  if (!spec.openapi || !String(spec.openapi).startsWith('3.')) {
    issues.push('Missing or non-3.x `openapi` version field.')
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
    modules: moduleFiles.map((f) => path.basename(f)),
    specPath: args.specPath,
    openapiVersion: spec.openapi,
    title: spec.info && spec.info.title,
    totalPaths: Object.keys(spec.paths || {}).length,
    totalOperations: endpoints.length,
    issues,
    endpoints,
  }
}

async function handleRunApiCollection(args) {
  if (!fs.existsSync(args.specPath)) {
    throw new Error(`OpenAPI file not found at ${args.specPath}`)
  }
  const spec = loadOpenApiSpec(args.specPath)
  const baseUrl = args.baseUrl.replace(/\/+$/, '')
  const httpMethods = args.onlyGetRequests
    ? ['get']
    : ['get', 'post', 'put', 'patch', 'delete']

  const results = []
  for (const [routePath, pathItem] of Object.entries(spec.paths || {})) {
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
      if (toolName === 'test_api_endpoint') {
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
