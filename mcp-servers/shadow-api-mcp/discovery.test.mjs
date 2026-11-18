import assert from 'node:assert/strict'
import { spawnSync } from 'node:child_process'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { test } from 'node:test'
import { fileURLToPath } from 'node:url'

const server = fileURLToPath(new URL('./index.mjs', import.meta.url))
const title = { title: 'Example API', version: '1.0.0' }
const operation = { summary: 'List users', operationId: 'listUsers', responses: { 200: { description: 'OK' } } }
const spec = { openapi: '3.1.0', info: title, paths: { '/users': { get: operation } } }
const yaml = 'openapi: 3.1.0\ninfo:\n  title: Example API\n  version: 1.0.0\npaths: {}\n'
const endpoint = { routePath: '/items', method: 'get', summary: 'List items' }

function fixture(t, files = {}) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'shadow-api-discovery-'))
  t.after(() => fs.rmSync(root, { recursive: true, force: true }))
  function write(file, body) {
    const absolute = path.join(root, file)
    fs.mkdirSync(path.dirname(absolute), { recursive: true })
    fs.writeFileSync(absolute, typeof body === 'string' ? body : JSON.stringify(body))
  }
  for (const [file, body] of Object.entries(files)) write(file, body)
  const absolute = (file) => path.join(root, file)
  function call(name, args = {}, expectError) {
    const result = spawnSync(process.execPath, [server], {
      input: JSON.stringify({ jsonrpc: '2.0', id: 1, method: 'tools/call', params: { name, arguments: { projectRoot: root, ...args } } }) + '\n',
      encoding: 'utf8',
      timeout: 10_000,
    })
    assert.equal(result.status, 0, result.stderr || result.error?.message)
    const response = JSON.parse(result.stdout).result
    if (expectError) {
      assert.equal(response.isError, true)
      assert.match(response.content[0].text, expectError)
      return
    }
    assert.equal(response.isError, false, response.content[0].text)
    return JSON.parse(response.content[0].text)
  }
  return {
    root, write, absolute, call,
    read: (file) => fs.readFileSync(absolute(file), 'utf8'),
    discover: (args) => call('discover_api_artifacts', args),
    upsert: (file, opts, error) => call('upsert_openapi_endpoint', { ...endpoint, specPath: absolute(file), ...opts }, error),
  }
}

for (const [name, file, document, kind] of [
  ['OpenAPI YAML under specs/', 'docs/specs/contract.yml', yaml, 'OPENAPI'],
  ['OpenAPI JSON with an unconventional filename', 'docs/contract.json', spec, 'OPENAPI'],
  ['Swagger 2.0', 'specs/public.json', { swagger: '2.0', info: title, paths: spec.paths }, 'SWAGGER'],
]) {
  test(name, (t) => {
    const f = fixture(t, { [file]: document })
    const result = f.discover()
    assert.equal(result.architecture, 'CONTRACT_FIRST')
    assert.deepEqual(result.sourceOfTruth, { type: kind, paths: [file], verified: false })
    assert.equal(result.systems[0].role, 'AUTHORITATIVE_SOURCE')
    assert.equal(result.requiresUserDecision, false)
    assert.equal(f.call('validate_openapi_spec', { specPath: f.absolute(file) }).valid, true)
  })
}

test('modular OpenAPI resolves local fragments without rewriting master or fragment', (t) => {
  const f = fixture(t, {
    'api/openapi.json': { ...spec, paths: { '/users': { $ref: './paths/users.json' } } },
    'api/paths/users.json': { get: operation },
  })
  const original = [f.read('api/openapi.json'), f.read('api/paths/users.json')]
  assert.deepEqual(f.discover().sourceOfTruth.paths, ['api/openapi.json', 'api/paths/users.json'])
  const validation = f.call('validate_openapi_spec', { specPath: f.absolute('api/openapi.json') })
  assert.equal(validation.valid, true)
  assert.equal(validation.totalOperations, 1)
  assert.equal(validation.layoutMode, 'modular')
  f.upsert('api/openapi.json', {}, /existing workflow for split references/)
  assert.deepEqual([f.read('api/openapi.json'), f.read('api/paths/users.json')], original)
})

const nest = {
  'package.json': { dependencies: { '@nestjs/swagger': '8.0.0' } },
  'src/bootstrap.ts': `import { SwaggerModule } from '@nestjs/swagger';
const config = new DocumentBuilder().setTitle('Users').build();
const document = SwaggerModule.createDocument(app, config);
SwaggerModule.setup('docs', app, document, { jsonDocumentUrl: '/schema.json' });`,
  'src/users/users.controller.ts': "@ApiTags('users')\n@Controller('users')\nclass UsersController { @Get() findAll() {} }",
}
const fastapi = { 'main.py': "from fastapi import FastAPI\napp = FastAPI(openapi_url='/spec/openapi.json')\n@app.get('/users')\ndef users(): return []" }
const express = {
  'package.json': { dependencies: { express: '4.21.0', 'swagger-jsdoc': '6.2.8' } },
  'app.js': "const swaggerJsdoc = require('swagger-jsdoc');\nconst spec = swaggerJsdoc({ definition, apis: ['./routes.js'] });",
  'routes.js': '/** @openapi\n * /users: \n *   get:\n */',
}

for (const [framework, files, source] of [
  ['nestjs', nest, 'src/users/users.controller.ts'],
  ['fastapi', fastapi, 'main.py'],
  ['express', express, 'routes.js'],
  ['django-rest-framework', {
    'requirements.txt': 'djangorestframework==3.15.2\ndrf-spectacular==0.28.0',
    'project/settings.py': 'REST_FRAMEWORK = {"DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema"}',
    'api/views.py': '@extend_schema(responses=UserSerializer)\ndef users(request): pass',
  }, 'api/views.py'],
  ['laravel', {
    'composer.json': { require: { 'darkaonline/l5-swagger': '^9.0' } },
    'Makefile': 'docs:\n\tphp artisan l5-swagger:generate',
    'app/Http/Controllers/UserController.php': "<?php\n/** @OA\\Get(path=\"/users\") */",
  }, 'app/Http/Controllers/UserController.php'],
  ['go', {
    'go.mod': 'module example.test/users\nrequire github.com/swaggo/swag v1.16.4',
    'Makefile': 'docs:\n\tswag init -g cmd/api/main.go',
    'cmd/api/main.go': 'package main\n// @Summary List users\n// @Router /users [get]\nfunc main() {}',
  }, 'cmd/api/main.go'],
  ['spring-boot', {
    'build.gradle': "implementation 'org.springdoc:springdoc-openapi-starter-webmvc-ui:2.8.0'",
    'src/main/java/com/example/Application.java': '@SpringBootApplication\nclass Application {}',
    'src/main/java/com/example/Users.java': '@RestController\nclass Users { @GetMapping("/users") List<User> list() {} }',
  }, 'src/main/java/com/example/Users.java'],
  ['aspnet-core', {
    'Api.csproj': '<Project Sdk="Microsoft.NET.Sdk.Web"><ItemGroup><PackageReference Include="Microsoft.AspNetCore.OpenApi" Version="9.0.0" /></ItemGroup></Project>',
    'Program.cs': 'builder.Services.AddOpenApi();\napp.MapOpenApi("/openapi/{documentName}.json");\napp.MapGet("/users", () => users);',
  }, 'Program.cs'],
]) {
  test(`${framework} verifies code-first ownership and blocks a competing spec`, (t) => {
    const f = fixture(t, files)
    const result = f.discover()
    assert.equal(result.framework, framework)
    assert.equal(result.architecture, 'CODE_FIRST')
    assert.equal(result.sourceOfTruth.type, 'CODE_DECLARATIONS')
    assert.equal(result.sourceOfTruth.verified, true)
    assert.ok(result.sourceOfTruth.paths.includes(source))
    assert.ok(result.systems[0].generator.entryPoints.length)
    assert.equal(result.decision, 'REUSE_EXISTING')
    f.upsert('docs/api/openapi.yaml', { allowNewSpec: true }, /competing REST documentation/)
    assert.equal(fs.existsSync(f.absolute('docs')), false)
  })
}

test('viewers distinguish external specs, repository files and evidenced generator endpoints', (t) => {
  const f = fixture(t, {
    ...fastapi,
    'docs/scalar.html': '<script>Scalar.createApiReference("#app", {url: "https://api.example.test/openapi.json"})</script>',
    'docs/redoc.html': '<redoc spec-url="generated.json"></redoc>',
    'docs/swagger.html': '<script>SwaggerUIBundle({url: "/spec/openapi.json"})</script>',
    'docs/generated.json': { ...spec, 'x-generated': true },
  })
  const result = f.discover()
  assert.equal(result.framework, 'fastapi')
  assert.deepEqual(result.presentation.map(({ type, role, consumes }) => [type, role, consumes.kind, consumes.target]), [
    ['Redoc', 'DOCUMENTATION_VIEWER', 'LOCAL_REPOSITORY_FILE', 'docs/generated.json'],
    ['Scalar', 'DOCUMENTATION_VIEWER', 'EXTERNAL_URL', 'https://api.example.test/openapi.json'],
    ['Swagger UI', 'DOCUMENTATION_VIEWER', 'GENERATOR_ENDPOINT', '/spec/openapi.json'],
  ])
  const original = f.read('docs/generated.json')
  f.upsert('docs/generated.json', { allowNewSpec: true }, /Generated or unresolved/)
  assert.equal(f.read('docs/generated.json'), original)
})

test('NestJS viewer binding distinguishes generated input from an unrelated document', (t) => {
  const boot = "import { SwaggerModule } from '@nestjs/swagger';\nconst output = () => SwaggerModule.createDocument(app, config);"
  const f = fixture(t, { ...nest, 'src/bootstrap.ts': boot + "\nSwaggerModule.setup('docs', app, output);" })
  assert.deepEqual(f.discover().presentation[0].consumes, { kind: 'IN_PROCESS_GENERATOR', target: 'src/bootstrap.ts' })
  f.write('src/bootstrap.ts', boot + "\nSwaggerModule.setup('docs', app, anotherDocument);")
  assert.deepEqual(f.discover().presentation[0].consumes, { kind: 'UNRESOLVED', target: null })
})

test('declared generation script ties an unmarked output to its workflow', (t) => {
  const f = fixture(t, {
    ...express,
    'package.json': { ...express['package.json'], scripts: { 'docs:build': 'swagger-jsdoc -d definition.js routes.js -o docs/generated.json' } },
    'docs/generated.json': spec,
  })
  const result = f.discover()
  assert.equal(result.framework, 'express')
  assert.deepEqual(result.generatedArtifacts[0].generator.commands, [{ configuration: 'package.json', script: 'docs:build' }])
  assert.equal(result.generatedArtifacts[0].role, 'GENERATED_ARTIFACT')
  f.upsert('docs/generated.json', {}, /Generated or unresolved/)
})

test('project configuration distinguishes a contract input from its generated bundle', (t) => {
  const f = fixture(t, {
    'package.json': { scripts: { bundle: 'redocly bundle specs/public.json --output published/public.json' } },
    'redocly.yaml': 'apis:\n  public:\n    root: specs/public.json\n',
    'specs/public.json': spec,
    'published/public.json': spec,
  })
  const result = f.discover()
  assert.deepEqual(result.sourceOfTruth, { type: 'OPENAPI', paths: ['specs/public.json'], verified: true })
  assert.deepEqual(result.generatedArtifacts[0].paths, ['published/public.json'])
  const before = f.read('published/public.json')
  f.upsert('specs/public.json')
  f.upsert('published/public.json', {}, /Generated or unresolved/)
  assert.equal(f.read('published/public.json'), before)
  const drift = f.call('compare_openapi_drift', { expectedPath: f.absolute('specs/public.json'), actualPath: f.absolute('published/public.json') })
  assert.deepEqual(drift.operations.missing, ['GET /items'])
})

test('TypeSpec explicit emitter owns output and preserves source declarations', (t) => {
  const f = fixture(t, {
    'main.tsp': '@service namespace Example; op list(): string;',
    'tspconfig.yaml': 'emit:\n  - "@typespec/openapi3"\noptions:\n  "@typespec/openapi3":\n    emitter-output-dir: api\n    output-file: emitted.json\n',
    'api/emitted.json': spec,
  })
  const result = f.discover()
  assert.deepEqual(result.sourceOfTruth, { type: 'TYPESPEC', paths: ['main.tsp'], verified: true })
  assert.deepEqual(result.generatedArtifacts[0].paths, ['api/emitted.json'])
  f.upsert('api/emitted.json', {}, /Generated or unresolved/)
})

test('AsyncAPI, GraphQL, gRPC and REST are isolated by protocol', (t) => {
  const f = fixture(t, {
    'events/pubsub.yml': 'asyncapi: 3.0.0\ninfo:\n  title: Events\n  version: 1.0.0\nchannels: {}',
    'graphql/schema.graphql': 'type Query { users: [User!]! }',
    'graphql/server.js': 'new ApolloServer({ schema, introspection: false });',
    'rpc/users.proto': 'syntax = "proto3"; service Users { rpc ListUsers(ListRequest) returns (ListResponse); }',
  })
  const result = f.discover()
  assert.deepEqual(result.protocols, ['ASYNCAPI', 'GRAPHQL', 'GRPC'])
  assert.equal(result.conflicts.length, 0)
  assert.ok(result.systems.some(({ type }) => type === 'GRAPHQL_INTROSPECTION_CONFIG'))
  assert.equal(f.discover({ targetProtocol: 'GRPC' }).sourceOfTruth.type, 'PROTOBUF_SERVICE')
  assert.equal(f.discover({ targetProtocol: 'ASYNCAPI' }).sourceOfTruth.type, 'ASYNCAPI')
  assert.equal(f.discover({ targetProtocol: 'REST' }).decision, 'ASK_FOR_DOCUMENTATION_CHOICE')
})

test('README summary leaves format open while dedicated references require ownership verification', (t) => {
  const f = fixture(t, { 'README.md': '## Public API\n\n`GET /items` returns items.' })
  const result = f.discover()
  assert.equal(result.decision, 'ASK_FOR_DOCUMENTATION_CHOICE')
  assert.equal(result.requiresUserDecision, true)
  assert.equal(result.architecture, 'UNVERIFIED')
  assert.equal(result.sourceOfTruth, null)
  assert.deepEqual(fs.readdirSync(f.root), ['README.md'])
  assert.equal(result.systems[0].role, 'SUPPLEMENTARY_DOCUMENTATION')
  f.upsert('docs/api/openapi.yaml', {}, /explicit user selection/)
  const selection = { protocol: 'REST', format: 'OpenAPI 3.1', approach: 'contract-first', location: 'docs/api/openapi.yaml' }
  assert.equal(f.discover({ selection }).decision, 'USE_EXPLICIT_SELECTION')
  f.upsert(selection.location, { allowNewSpec: true })
  const dedicated = fixture(t, { 'docs/api-reference.md': '## API reference\nGET /items' })
  assert.equal(dedicated.discover().decision, 'VERIFY_OWNERSHIP')
  dedicated.upsert(selection.location, { allowNewSpec: true }, /competing REST documentation/)
  const viewer = fixture(t, { 'docs/index.html': '<redoc spec-url="https://example.test/schema.json"></redoc>' })
  assert.equal(viewer.discover().decision, 'VERIFY_OWNERSHIP')
})

test('existing client formats are independent of API authority', (t) => {
  const f = fixture(t, {
    'tools/bruno/bruno.json': { name: 'Users' },
    'tools/users.postman_collection.json': { info: title, item: [] },
    'tools/insomnia-export.json': {},
    'tools/hoppscotch-export.json': [],
    'tools/thunderCollection.json': [],
    'tools/smoke.http': 'GET https://example.test/users',
    'tools/update.rest': 'POST https://example.test/users',
  })
  const result = f.discover()
  assert.equal(result.detectedCollectionFormat, 'multiple_with_bruno')
  assert.equal(result.clientCollections.length, 7)
  assert.ok(result.clientCollections.every(({ role }) => role === 'CLIENT_COLLECTION'))
  assert.equal(result.sourceOfTruth, null)
})

test('conflicting generators prevent edits even with an exact path and allowNewSpec', (t) => {
  const f = fixture(t, { ...nest, ...fastapi, 'openapi.json': spec })
  const original = f.read('openapi.json')
  const result = f.discover()
  assert.equal(result.compatibility, 'CONFLICT_REQUIRES_DECISION')
  assert.equal(result.requiresUserDecision, true)
  assert.equal(result.sourceOfTruth, null)
  assert.equal(result.systems.filter(({ role }) => role === 'UNKNOWN').length, 3)
  f.upsert('openapi.json', { allowNewSpec: true }, /resolved REST ownership/)
  f.call('sync_postman_collection', { specPath: f.absolute('openapi.json'), force: true }, /Resolve REST documentation ownership/)
  assert.equal(f.read('openapi.json'), original)
})

test('negative probes reject unrelated YAML, passive dependencies, comments, samples and message-only protobuf', (t) => {
  const f = fixture(t, {
    'package.json': { ...nest['package.json'], scripts: { demo: 'echo swagger-jsdoc -o fake.json' } },
    'app.ts': '// SwaggerModule.createDocument(app, options)',
    'config.yaml': 'openapi: a-setting\ncomponents: {storage: redis}\npaths: {home: /tmp}',
    'types.proto': 'message User { string name = 1; }',
    'examples/main.py': fastapi['main.py'],
    'examples/openapi.json': spec,
    'docs/example.html': '<!-- <redoc spec-url="fake.json"></redoc> -->',
    'fake.json': { openapi: '3.1.0', paths: [] },
    'README.md': '# API design\nWork in progress.',
  })
  const result = f.discover()
  assert.equal(result.status, 'NOT_FOUND')
  assert.equal(result.systems.length, 0)
  assert.equal(result.modularFragments.length, 0)
  assert.equal(result.dependencyHints[0].tool, '@nestjs/swagger')
  assert.equal(result.decision, 'ASK_FOR_DOCUMENTATION_CHOICE')
  assert.equal(result.requiresUserDecision, true)
  assert.equal(fixture(t, { 'main.py': 'from fastapi import FastAPI\napp = FastAPI(openapi_url=None)' }).discover().status, 'NOT_FOUND')
})

test('generated marker handles real headers and explicit false flags differently', (t) => {
  const f = fixture(t, { 'authored.json': { ...spec, 'x-generated': false }, 'generated.yml': '# Code generated by the local bundle\n' + yaml })
  const result = f.discover()
  assert.deepEqual(result.sourceOfTruth.paths, ['authored.json'])
  assert.deepEqual(result.generatedArtifacts[0].paths, ['generated.yml'])
  f.upsert('generated.yml', {}, /Generated or unresolved/)
  f.upsert('authored.json')
  assert.equal(JSON.parse(f.read('authored.json'))['x-generated'], false)
})

test('greenfield without dependencies only creates the exact explicitly selected spec', (t) => {
  const f = fixture(t)
  assert.equal(f.discover().decision, 'ASK_FOR_DOCUMENTATION_CHOICE')
  f.upsert('docs/api/openapi.yaml', {}, /explicit user selection/)
  const selection = { protocol: 'REST', format: 'OpenAPI 3.1', location: 'contracts/public.yml', approach: 'contract-first' }
  const result = f.discover({ selection })
  assert.equal(result.decision, 'USE_EXPLICIT_SELECTION')
  assert.equal(result.requiresUserDecision, false)
  assert.equal(result.compatibility, 'COMPATIBLE')
  assert.equal(f.discover({ selection: { ...selection, protocol: 'GRAPHQL' } }).compatibility, 'INCOMPATIBLE')
  assert.equal(f.discover({ selection: { ...selection, location: '../elsewhere.yml' } }).compatibility, 'INCOMPATIBLE')
  assert.equal(f.discover({ selection: { ...selection, approach: 'local-custom-generator' } }).decision, 'VERIFY_SELECTION_COMPATIBILITY')
  assert.equal(f.call('bulk_upsert_openapi_endpoints', {
    specPath: f.absolute(selection.location), allowNewSpec: true, endpoints: [endpoint, { ...endpoint, routePath: '/users' }],
  }).totalUpserted, 2)
  assert.deepEqual(fs.readdirSync(f.root), ['contracts'])
  assert.deepEqual(fs.readdirSync(f.absolute('contracts')), ['public.yml'])
  assert.match(f.read(selection.location), /^openapi: 3\.1\.0/m)
})

test('bulk updates a compact authoritative spec while preserving custom collections, tests and environment', (t) => {
  const f = fixture(t, {
    'spec.json': spec,
    'clients/users.postman_collection.json': { info: title, item: [{ name: 'Users', event: [{ listen: 'test', script: { exec: ['custom test'] } }] }] },
    'clients/users.postman_environment.json': { values: [{ key: 'baseUrl', value: 'custom' }] },
  })
  const paths = ['clients/users.postman_collection.json', 'clients/users.postman_environment.json']
  const before = paths.map(f.read)
  const authoredOperation = { ...operation, deprecated: true, 'x-owner': 'users', responses: { 200: { description: 'OK', headers: { ETag: { schema: { type: 'string' } } } } } }
  f.write('spec.json', { ...spec, paths: { '/users': { get: authoredOperation } } })
  f.call('bulk_upsert_openapi_endpoints', {
    specPath: f.absolute('spec.json'), endpoints: [endpoint, { routePath: '/users', method: 'get', summary: 'Find users', responses: { 200: { description: 'Success' } } }], collectionFormat: 'postman',
  })
  assert.ok(JSON.parse(f.read('spec.json')).paths['/items'])
  const updated = JSON.parse(f.read('spec.json')).paths['/users'].get
  assert.equal(updated.operationId, authoredOperation.operationId)
  assert.equal(updated['x-owner'], 'users')
  assert.deepEqual(updated.responses[200].headers, authoredOperation.responses[200].headers)
  f.call('sync_postman_collection', { specPath: f.absolute('spec.json'), force: true }, /is protected/)
  assert.deepEqual(paths.map(f.read), before)
})

test('Postman initialization and a new OpenAPI file both require explicit intent', (t) => {
  const f = fixture(t, { 'openapi.json': spec, 'bruno/bruno.json': { name: 'Existing' } })
  f.call('sync_postman_collection', { specPath: f.absolute('openapi.json') }, /Only|Refusing/i)
  f.upsert('second.json', { allowNewSpec: true }, /competing REST documentation/)
  assert.deepEqual(fs.readdirSync(f.root), ['bruno', 'openapi.json'])
})

test('explicit Postman initialization creates only its authorized collection and environment', (t) => {
  const f = fixture(t, { 'source.json': spec })
  const initialized = f.call('sync_postman_collection', {
    specPath: f.absolute('source.json'), force: true, collectionOutputPath: f.absolute('clients/postman_collection.json'),
  })
  assert.equal(initialized.status, 'synced')
  assert.deepEqual(fs.readdirSync(f.root), ['clients', 'source.json'])
  assert.deepEqual(fs.readdirSync(f.absolute('clients')), ['postman_collection.json', 'postman_environment.json'])
  assert.deepEqual(JSON.parse(f.read('source.json')), spec)
})

test('scope boundary rejects symlink and junction targets', (t) => {
  const inside = fixture(t)
  const outside = fixture(t, { 'authored.json': spec })
  fs.symlinkSync(outside.root, inside.absolute('linked'), process.platform === 'win32' ? 'junction' : 'dir')
  assert.equal(inside.discover().status, 'NOT_FOUND')
  inside.upsert('linked/authored.json', {}, /symbolic link/)
  assert.deepEqual(JSON.parse(outside.read('authored.json')), spec)
})

test('live-recording ownership guard fails before HTTP and project boundaries block writes', (t) => {
  const f = fixture(t, { 'generated.json': { ...spec, 'x-generated': true }, 'local.json': spec })
  const sibling = fixture(t, { 'outside.json': spec })
  assert.equal(f.discover().systems.some(({ paths }) => paths.includes('outside.json')), false)
  f.call('test_api_endpoint', { url: 'not-a-url', method: 'GET', recordToOpenApiPath: f.absolute('generated.json') }, /Generated or unresolved/)
  f.call('upsert_openapi_endpoint', { ...endpoint, specPath: sibling.absolute('outside.json') }, /outside projectRoot/)
  f.call('sync_postman_collection', { specPath: f.absolute('local.json'), collectionOutputPath: sibling.absolute('new.json'), force: true }, /outside projectRoot/)
  assert.deepEqual(JSON.parse(sibling.read('outside.json')), spec)
  assert.equal(fs.existsSync(sibling.absolute('new.json')), false)
})

test('discovery does not execute generator scripts, package installs, or live/load verification', (t) => {
  const f = fixture(t, {
    'package.json': { scripts: { 'docs:build': 'swagger-jsdoc -o output.json; npm install; node sentinel.js' } },
    'sentinel.js': 'require("node:fs").writeFileSync("executed.txt", "unexpected")',
    'output.json': spec,
  })
  const before = fs.readdirSync(f.root)
  const result = f.discover()
  assert.equal(result.generatedArtifacts[0].role, 'GENERATED_ARTIFACT')
  assert.deepEqual(fs.readdirSync(f.root), before)
})

test('read-only drift detects operation and schema changes and supports explicit internal exclusions', (t) => {
  const f = fixture(t, {
    'baseline.json': { ...spec, components: { schemas: { User: { type: 'string' } } } },
    'generated.json': {
      ...spec, 'x-generated': true, paths: {
        '/users': { get: { ...operation, responses: { 202: { description: 'Accepted' } } } },
        '/internal/health': { get: operation },
      },
      components: { schemas: { User: { type: 'number' } } },
    },
  })
  const compare = f.call('compare_openapi_drift', {
    expectedPath: f.absolute('baseline.json'), actualPath: f.absolute('generated.json'), internalOperations: ['GET /internal/health'],
  })
  assert.equal(compare.status, 'DRIFT_FOUND')
  assert.deepEqual(compare.operations, { missing: [], unexpected: [], changed: ['GET /users'] })
  assert.deepEqual(compare.schemas.changed, ['User'])
  assert.equal(f.call('compare_openapi_drift', { expectedPath: f.absolute('baseline.json'), actualPath: f.absolute('baseline.json') }).status, 'MATCH')
  assert.equal(JSON.parse(f.read('generated.json')).components.schemas.User.type, 'number')
})

test('unresolvable references report uncertainty without fetching remote targets', (t) => {
  const f = fixture(t, {
    'local.json': spec,
    'remote.json': { ...spec, paths: { '/users': { $ref: 'https://example.invalid/contract.json#/paths/users' } } },
  })
  assert.equal(f.call('validate_openapi_spec', { specPath: f.absolute('remote.json') }).valid, false)
  assert.equal(f.call('compare_openapi_drift', { expectedPath: f.absolute('local.json'), actualPath: f.absolute('remote.json') }).status, 'UNVERIFIED')
})

test('incomplete evidence blocks new documentation writes', (t) => {
  const f = fixture(t, { 'src/large.ts': ' '.repeat(257 * 1024) })
  const result = f.discover()
  assert.equal(result.status, 'INCOMPLETE')
  assert.equal(result.coverage.incomplete, true)
  assert.equal(result.decision, 'VERIFY_OWNERSHIP')
  f.upsert('openapi.json', { allowNewSpec: true }, /complete discovery/)
  assert.equal(fs.existsSync(f.absolute('openapi.json')), false)
})

test('a service root confines discovery in a monorepo with multiple generators', (t) => {
  const f = fixture(t, {
    ...Object.fromEntries(Object.entries(nest).map(([file, content]) => [`apps/users/${file}`, content])),
    ...Object.fromEntries(Object.entries(fastapi).map(([file, content]) => [`apps/catalog/${file}`, content])),
  })
  assert.equal(f.discover().compatibility, 'CONFLICT_REQUIRES_DECISION')
  const service = f.discover({ projectRoot: f.absolute('apps/users'), targetProtocol: 'REST' })
  assert.equal(service.framework, 'nestjs')
  assert.ok(service.sourceOfTruth.paths.includes('src/bootstrap.ts'))
  assert.equal(service.conflicts.length, 0)
})

test('a bounded repository generator workflow brings an output back into sync', (t) => {
  const f = fixture(t, {
    'redocly.yaml': 'apis:\n  api:\n    root: contract.json\n',
    'contract.json': spec,
    'generated/public.json': { ...spec, 'x-generated': true },
    'scripts/bundle.cjs': `const fs = require('node:fs')
const source = JSON.parse(fs.readFileSync('contract.json', 'utf8'))
fs.writeFileSync('generated/public.json', JSON.stringify({ ...source, 'x-generated': true }))
`,
  })
  const compare = () => f.call('compare_openapi_drift', { expectedPath: f.absolute('contract.json'), actualPath: f.absolute('generated/public.json') })
  f.upsert('contract.json')
  assert.equal(compare().status, 'DRIFT_FOUND')
  const generated = spawnSync(process.execPath, [f.absolute('scripts/bundle.cjs')], { cwd: f.root, encoding: 'utf8' })
  assert.equal(generated.status, 0, generated.stderr)
  assert.equal(compare().status, 'MATCH')
  assert.equal(f.call('validate_openapi_spec', { specPath: f.absolute('generated/public.json') }).valid, true)
  assert.deepEqual(fs.readdirSync(f.absolute('generated')), ['public.json'])
})

const codeFirstWorkflow = {
  'package.json': { dependencies: { express: '5.2.1' }, scripts: {
    'api-docs': 'tsx src/scripts/generate-openapi.ts',
    'api-docs:check': 'tsx src/scripts/generate-openapi.ts --check',
  } },
  'src/scripts/generate-openapi.ts': `
import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { generateOpenApi } from "../docs/openapi.js";
const artifact = resolve("dist/docs/openapi.json");
const generated = JSON.stringify(generateOpenApi(), null, 2);
await writeFile(artifact, generated);
`,
  'src/docs/openapi.ts': `
import { endpointRegistry, type EndpointDefinition } from "../core/endpoint-registry.js";
export function generateOpenApi() {
  const paths = toPaths(endpointRegistry);
  return { openapi: "3.1.0", info, paths };
}
`,
  'src/core/endpoint-registry.ts': `
export const endpointRegistry = {
  "docs.spec": { method: "GET", path: "/docs/openapi.json", module: "docs" },
};
`,
  'src/docs/swagger.ts': `
import { generateOpenApi } from "./openapi.js";
const spec = generateOpenApi();
mountEndpoint(app, "docs.spec", (_req, res) => {
  res.json(spec);
});
swaggerUi.setup(undefined, { swaggerOptions: { url: "/docs/openapi.json" } });
`,
  'docs/REFERENCE.md': '## API endpoints\n\n`GET /docs/openapi.json` returns the contract.',
}

test('repository generator traces builder, registry, commands, ignored output and viewer', (t) => {
  const f = fixture(t, { ...codeFirstWorkflow, 'dist/docs/openapi.json': spec })
  const hashInput = f.read('dist/docs/openapi.json')
  const result = f.discover()
  assert.equal(result.architecture, 'CODE_FIRST')
  assert.equal(result.framework, 'express')
  assert.equal(result.decision, 'REUSE_EXISTING')
  assert.deepEqual(result.sourceOfTruth, {
    type: 'CODE_DECLARATIONS', paths: ['src/docs/openapi.ts', 'src/core/endpoint-registry.ts'], verified: true,
  })
  assert.deepEqual(result.systems[0].generator.commands.map(({ script, mode }) => [script, mode]), [['api-docs', 'GENERATE'], ['api-docs:check', 'CHECK']])
  assert.deepEqual(result.generatedArtifacts[0].paths, ['dist/docs/openapi.json'])
  assert.equal(result.generatedArtifacts[0].present, true)
  assert.deepEqual(result.presentation[0].consumes, { kind: 'GENERATOR_ENDPOINT', target: '/docs/openapi.json' })
  f.upsert('dist/docs/openapi.json', {}, /Generated or unresolved/)
  f.upsert('docs/api/openapi.yaml', { allowNewSpec: true }, /competing REST documentation/)
  assert.equal(f.read('dist/docs/openapi.json'), hashInput)
  assert.equal(fs.existsSync(f.absolute('docs/api')), false)
})

test('custom workflow leaves a mismatched viewer unresolved and can identify a declared output before generation', (t) => {
  const f = fixture(t, { ...codeFirstWorkflow, 'src/docs/swagger.ts': codeFirstWorkflow['src/docs/swagger.ts'].replace('/docs/openapi.json', '/docs/other.json') })
  const result = f.discover()
  assert.equal(result.sourceOfTruth.verified, true)
  assert.equal(result.generatedArtifacts[0].present, false)
  assert.equal(result.presentation[0].consumes.kind, 'URL_OR_PATH')
})

test('script name and viewer alone do not establish a repository generator or Markdown fallback', (t) => {
  const f = fixture(t, { ...codeFirstWorkflow,
    'src/scripts/generate-openapi.ts': codeFirstWorkflow['src/scripts/generate-openapi.ts'].replace('await writeFile(artifact, generated);', '// await writeFile(artifact, generated);'),
  })
  const result = f.discover()
  assert.equal(result.sourceOfTruth, null)
  assert.equal(result.generatedArtifacts.length, 0)
  assert.equal(result.decision, 'VERIFY_OWNERSHIP')
})
