import fs from 'node:fs'
import path from 'node:path'
import YAML from 'yaml'
import { findRepositoryGenerators, servesRepositoryGenerator } from './repository-generators.mjs'

export const relativePath = (root, file) => path.relative(root, file).split(path.sep).join('/')

export function isWithin(root, file) {
  const relative = path.relative(root, file)
  return relative !== '..' && !relative.startsWith(`..${path.sep}`) && !path.isAbsolute(relative)
}

export function assertProjectPath(root, file) {
  const absolute = path.resolve(file)
  if (!isWithin(root, absolute)) throw new Error('Path is outside projectRoot.')
  for (let current = absolute; ; current = path.dirname(current)) {
    try {
      if (fs.lstatSync(current).isSymbolicLink()) throw new Error('Project path traverses a symbolic link.')
    } catch (error) {
      if (error.code !== 'ENOENT') throw error
    }
    if (path.relative(root, current) === '') break
  }
  return absolute
}

const RELATIVE_FILE = /^(?![\\/]|\w+:)[\w./-]+\.(?:json|ya?ml|tsp|graphqls?|gql|proto|md)$/i
const GENERATED = /^\s*(?:#|\/\/|<!--)\s*(?:@generated\b|(?:this file is )?(?:auto[- ]?)generated\b|code generated\b)/im
const SOURCE_EXTENSIONS = /\.(?:[cm]?[jt]sx?|py|php|go|java|kt|cs)$/i
export function isSamplePath(file) {
  const segments = file.split('/')
  const sourceIndex = segments.findIndex((segment) => /^(?:src|app|lib|cmd)$/i.test(segment))
  const directorySegments = segments.slice(0, -1)
  const projectFolders = sourceIndex === -1 ? directorySegments : directorySegments.slice(0, sourceIndex)
  return projectFolders.some((segment) => /^(?:tests?|__tests__|fixtures?|examples|samples)$/i.test(segment))
    || /(?:^|\/)src\/test\//i.test(file)
}
const DOCUMENT_CONFIG = /^(?:package\.json|(?:pyproject|uv)\.toml|requirements[^/]*\.txt|Pipfile|composer\.json|go\.mod|pom\.xml|build\.gradle(?:\.kts)?|.*\.csproj|(?:Makefile|Taskfile\.ya?ml|tspconfig\.ya?ml|l5-swagger\.php|application(?:-[\w-]+)?\.(?:ya?ml|properties))|.*\.(?:sh|ps1))$/i
const WORKFLOW_CONFIG = /(?:^|\/)(?:\.github\/workflows\/[^/]+\.ya?ml|Makefile|Taskfile\.ya?ml|tspconfig\.ya?ml|redocly\.ya?ml|\.redocly\.ya?ml)$/i

const GENERATORS = [
  ['nestjs', '@nestjs/swagger', /@nestjs\/swagger/, /\bSwaggerModule\.createDocument\s*\(/, /@(?:Api\w+|Controller)\s*\(/],
  ['express', 'swagger-jsdoc', /\bswagger-jsdoc\b/, /\b(?:swaggerJsdoc|swaggerJSDoc|swaggerJsDoc)\s*\(/, /@(?:openapi|swagger)\b/],
  ['fastapi', 'FastAPI', /\b(?:from|import)\s+fastapi\b/i, /\bFastAPI\s*\(/, /@\w+\.(?:get|post|put|patch|delete|head|options|api_route)\s*\(/],
  ['django-rest-framework', 'drf-spectacular', /\bdrf[-_]spectacular\b/i, /\bdrf_spectacular\.openapi\.AutoSchema\b|\bSpectacularAPIView\.as_view\s*\(/, /@extend_schema\s*\(/],
  ['laravel', 'L5-Swagger', /darkaonline\/l5-swagger/i, /\bl5-swagger:generate\b|\bL5SwaggerServiceProvider\b/, /@OA\\\w+\b|#\[OA\\\w+/],
  ['go', 'swaggo/swag', /github\.com\/swaggo\/swag\b/, /\bswag\s+init\b|\b(?:ginSwagger|httpSwagger|echoSwagger)\.WrapHandler\b/, /^\s*\/\/\s*@(?:Router|Summary|Success)\b/m],
  ['spring-boot', 'springdoc-openapi', /\bspringdoc-openapi[\w-]*/, /\bspring-boot-(?:starter-web(?:flux)?|gradle-plugin)\b|@SpringBootApplication\b/, /@(?:RestController|Operation|RequestMapping|GetMapping|PostMapping)\b/],
  ['aspnet-core', 'ASP.NET Core OpenAPI', /Microsoft\.AspNetCore\.OpenApi|Swashbuckle\.AspNetCore|NSwag\.AspNetCore/i, /\.(?:AddOpenApi|AddSwaggerGen|AddOpenApiDocument)\s*\(/, /\.(?:MapGet|MapPost|MapPut|MapDelete|MapPatch|WithOpenApi)\s*\(|\[Http(?:Get|Post|Put|Delete|Patch)\b/],
]

function uncommentedCode(raw) {
  return raw.replace(/<!--[\s\S]*?-->|\/\*[\s\S]*?\*\//g, '').replace(/^\s*(?:\/\/|#(?!\[)).*$/gm, '')
}

function artifact(role, protocol, type, paths, evidence, extra = {}) {
  return { role, protocol, type, paths, evidence, ...extra }
}

function localFile(from, target, files) {
  if (!RELATIVE_FILE.test(target)) return null
  const resolved = path.posix.normalize(path.posix.join(path.posix.dirname(from), target))
  return files.has(resolved) ? resolved : null
}

function declaredCommands(records) {
  const commands = []
  for (const { file, raw } of records) {
    if (WORKFLOW_CONFIG.test(file) || /\.(?:sh|ps1)$/i.test(file)) {
      for (const [offset, line] of raw.split(/\r?\n/).entries()) {
        if (/^\s*(?:-\s+)?(?:run:\s*|\t)?(?:npx\s+|uv run\s+)?(?:redocly\s+bundle|swagger-cli\s+bundle|tsp\s+compile|swag\s+init|swagger-jsdoc\b|python\s+manage\.py\s+spectacular|php\s+artisan\s+l5-swagger:generate)\b/.test(line)) {
          commands.push({ configuration: file, line: offset + 1, value: line, base: /^(?:\.github\/workflows\/)/.test(file) ? 'package.json' : file })
        }
      }
    }
    if (!file.endsWith('package.json')) continue
    try {
      for (const [script, value] of Object.entries(JSON.parse(raw).scripts || {})) {
        if (typeof value !== 'string' || !/^[\w:-]+$/.test(script)) continue
        if (/^\s*(?:(?:npx|uv run)\s+)?(?:swagger-jsdoc|swag\s+init|redocly|swagger-cli|tsp\s+compile|python\s+manage\.py\s+spectacular|php\s+artisan\s+l5-swagger:generate|openapi-generator)\b/.test(value)) {
          commands.push({ configuration: file, script, value, base: file })
        }
      }
    } catch {
      // Invalid manifests cannot establish a workflow.
    }
  }
  return commands
}

function findViewers(records, files) {
  const patterns = [
    ['Scalar', /\bScalar\.createApiReference\s*\(|<api-reference\b|\bMapScalarApiReference\s*\(/gi],
    ['Redoc', /<redoc\b|\bRedoc\.init\s*\(/gi],
    ['RapiDoc', /<rapi-doc\b/gi],
    ['Swagger UI', /\bSwaggerUIBundle\s*\(|\bswaggerUi\.setup\s*\(|\bUseSwaggerUI\s*\(|\bSwaggerModule\.setup\s*\(/g],
  ]
  const viewers = []
  for (const { file, code } of records) {
    if (!SOURCE_EXTENSIONS.test(file) && !file.endsWith('.html')) continue
    for (const [tool, pattern] of patterns) {
      for (const match of code.matchAll(pattern)) {
        const invocation = code.slice(match.index, match.index + 1500).split(/;|<\/(?:script|redoc|api-reference)\b/i)[0]
        const target = invocation.match(/\b(?:spec-url|data-url|jsonDocumentUrl|url)\s*[:=]\s*['"]([^'"\s]+)['"]/i)?.[1]
          || invocation.match(/\bRedoc\.init\s*\(\s*['"]([^'"\s]+)['"]/)?.[1]
        // Reject credential-bearing URLs and discard query/fragment data.
        const consumer = target && !/[?&#@]/.test(target) ? target : null
        const local = consumer && localFile(file, consumer, files)
        viewers.push(artifact('DOCUMENTATION_VIEWER', 'REST', tool, [file], ['Viewer invocation or markup'], {
          configured: true,
          consumes: local ? { kind: 'LOCAL_REPOSITORY_FILE', target: local }
            : consumer ? { kind: /^https?:\/\//i.test(consumer) ? 'EXTERNAL_URL' : 'URL_OR_PATH', target: consumer }
              : { kind: 'UNRESOLVED', target: null },
        }))
      }
    }
  }
  return viewers
}

function buildSystems(records, commands) {
  const systems = []
  const dependencyHints = []
  for (const [framework, tool, dependency, integration, declarations] of GENERATORS) {
    const dependencies = records.filter(({ file, raw, code }) => {
      const name = path.posix.basename(file)
      if (name === 'package.json' || name === 'composer.json') {
        try {
          const manifest = JSON.parse(raw)
          return ['dependencies', 'devDependencies', 'optionalDependencies', 'require', 'require-dev']
            .some((section) => Object.keys(manifest?.[section] || {}).some((key) => dependency.test(key)))
        } catch {
          return false
        }
      }
      return DOCUMENT_CONFIG.test(name) && dependency.test(code)
    }).map(({ file }) => file)
    const frameworkFiles = records.filter(({ file, code }) => (
      (SOURCE_EXTENSIONS.test(file) || DOCUMENT_CONFIG.test(path.posix.basename(file))) && integration.test(code)
      || framework === 'laravel' && /(?:^|\/)config\/l5-swagger\.php$/.test(file) && /['"]documentations['"]\s*=>/.test(code)
    ))
    const sources = records.filter(({ file, raw, code }) => SOURCE_EXTENSIONS.test(file) && declarations.test(['express', 'go', 'laravel'].includes(framework) ? raw : code)).map(({ file }) => file)
    const invocations = frameworkFiles.filter(({ file, code }) => SOURCE_EXTENSIONS.test(file) && dependency.test(code))
    const generatorCommands = commands.filter(({ value }) => integration.test(value) || (framework === 'express' && /\bswagger-jsdoc\b/.test(value)))
    const entryPoints = [...new Set([...frameworkFiles.map(({ file }) => file), ...generatorCommands.map(({ configuration }) => configuration)])]
    if (!entryPoints.length || (!dependencies.length && !invocations.length)) {
      if (dependencies.length) dependencyHints.push({ framework, tool, paths: dependencies })
      continue
    }
    const disabled = framework === 'fastapi' && frameworkFiles.every(({ code }) => /\bopenapi_url\s*=\s*None\b/.test(code) && !/\.openapi\s*\(/.test(code))
    if (disabled || (['go', 'laravel'].includes(framework) && !sources.length)) {
      dependencyHints.push({ framework, tool, paths: [...new Set([...dependencies, ...entryPoints])] })
      continue
    }
    systems.push(artifact('AUTHORITATIVE_SOURCE', 'REST', 'CODE_DECLARATIONS', [...new Set([...entryPoints, ...sources])],
      ['Generator dependency or import', 'Framework integration or generation entry point'], {
        architecture: 'CODE_FIRST', framework, confidence: 'SUPPORTED_BY_REPOSITORY',
        generator: { tool, entryPoints, dependencies, commands: generatorCommands.map(commandLocation) },
        outputEndpoints: [...new Set(frameworkFiles.flatMap(({ code }) =>
          Array.from(code.matchAll(/(?:\bopenapi_url\s*=\s*|\bMapOpenApi\s*\(\s*|\bjsonDocumentUrl\s*:\s*)['"]([\w/{}.\-]+)['"]/g), ([, endpoint]) => endpoint)))],
        synchronization: 'Update framework declarations and regenerate through the existing workflow.',
      }))
  }
  return { systems, dependencyHints }
}

function otherDocumentation(records) {
  const documents = []
  for (const { file, code, raw } of records) {
    if (/\.tsp$/i.test(file) && /\b(?:model|namespace|interface|op)\s+\w+/.test(code)) {
      const entry = /@service\b|\bop\s+\w+\s*\(/.test(code)
      documents.push(artifact(entry ? 'AUTHORITATIVE_SOURCE' : 'UNKNOWN', 'REST', 'TYPESPEC', [file], ['TypeSpec declarations'], { architecture: 'CONTRACT_FIRST' }))
    } else if (/\.(?:graphqls?|gql)$/i.test(file) && /\b(?:type|extend\s+type)\s+(?:Query|Mutation|Subscription)\b|\bschema\s*\{/.test(raw.replace(/^\s*#.*$/gm, ''))) {
      documents.push(artifact(GENERATED.test(raw) ? 'GENERATED_ARTIFACT' : 'AUTHORITATIVE_SOURCE', 'GRAPHQL', 'GRAPHQL_SCHEMA', [file], ['GraphQL root operation declarations'], { architecture: 'CONTRACT_FIRST' }))
    } else if (/\.proto$/i.test(file) && /\bservice\s+\w+\s*\{[\s\S]*?\brpc\s+\w+\s*\(/.test(code)) {
      documents.push(artifact(GENERATED.test(raw) ? 'GENERATED_ARTIFACT' : 'AUTHORITATIVE_SOURCE', 'GRPC', 'PROTOBUF_SERVICE', [file], ['Protobuf service and RPC declarations'], { architecture: 'CONTRACT_FIRST' }))
    } else if (/\.md$/i.test(file) && /^(?:#{1,4}\s+.*\b(?:API|endpoints?)\b)/im.test(raw) && /\b(?:GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+\//.test(raw)) {
      documents.push(artifact('SUPPLEMENTARY_DOCUMENTATION', 'REST', 'MARKDOWN_API_REFERENCE', [file], ['API heading and HTTP endpoint example'], { architecture: 'DOCUMENTATION_FIRST' }))
    } else if (/\b(?:ApolloServer|createYoga|GraphQLModule\.forRoot)\b/.test(code) && /\bintrospection\s*:/.test(code) && SOURCE_EXTENSIONS.test(file)) {
      documents.push(artifact('UNKNOWN', 'GRAPHQL', 'GRAPHQL_INTROSPECTION_CONFIG', [file], ['GraphQL server and introspection setting']))
    }
  }
  return documents
}

function commandLocation({ configuration, script, line }) {
  return { configuration, ...(script ? { script } : { line }) }
}

function selectionCompatibility(root, selection) {
  if (!selection || !['protocol', 'format', 'location', 'approach'].every((key) => typeof selection[key] === 'string' && selection[key].trim())) return 'UNKNOWN'
  try {
    assertProjectPath(root, path.resolve(root, selection.location))
  } catch {
    return 'INCOMPATIBLE'
  }
  const protocol = selection.protocol.toUpperCase()
  const format = selection.format.toLowerCase()
  const inferred = /openapi|swagger/.test(format) ? 'REST' : /asyncapi/.test(format) ? 'ASYNCAPI'
    : /graphql/.test(format) ? 'GRAPHQL' : /protobuf|grpc/.test(format) ? 'GRPC' : null
  if (inferred && protocol !== inferred) return 'INCOMPATIBLE'
  if (format === 'openapi 3.1' && /^contract[-_ ]first$/i.test(selection.approach) && /\.(?:json|ya?ml)$/i.test(selection.location)) return 'COMPATIBLE'
  return 'UNKNOWN'
}

function documentationDecision({ ambiguous, authorities, markdownOnly, selection, status, compatibility }) {
  if (ambiguous) return 'VERIFY_OWNERSHIP'
  if (authorities.length) return 'REUSE_EXISTING'
  if (markdownOnly && !selection) return 'REUSE_MARKDOWN'
  if (status !== 'NOT_FOUND') return 'VERIFY_OWNERSHIP'
  if (compatibility === 'INCOMPATIBLE') return 'REVIEW_INCOMPATIBLE_SELECTION'
  if (compatibility === 'COMPATIBLE') return 'USE_EXPLICIT_SELECTION'
  return selection ? 'VERIFY_SELECTION_COMPATIBILITY' : 'ASK_FOR_DOCUMENTATION_CHOICE'
}

function consumesNestGenerator(code) {
  const bindings = new Set(Array.from(code.matchAll(/\b(?:const|let|var)\s+(\w+)\s*=\s*(?:\([^)]*\)\s*=>\s*)?SwaggerModule\.createDocument\s*\(/g), ([, name]) => name))
  const viewerInput = code.match(/\bSwaggerModule\.setup\s*\([^,]+,[^,]+,\s*(\w+)\b/)?.[1]
  return bindings.has(viewerInput)
}

export function describeDocumentation(root, files, specs, collections, coverage, selection, targetProtocol, inspectOutput) {
  const fileSet = new Set(files.map(({ file }) => file))
  const records = files.filter(({ file, raw }) => raw && !isSamplePath(file)).map(({ file, raw }) => ({ file, raw, code: uncommentedCode(raw) }))
  const commands = declaredCommands(records)
  const { systems, dependencyHints } = buildSystems(records, commands)
  const workflows = findRepositoryGenerators(records)
  const workflowByOutput = new Map()
  for (const workflow of workflows) {
    const { producer, inputs, entryPoints, outputPaths, framework, commands } = workflow
    for (const output of outputPaths) workflowByOutput.set(output, workflow)
    systems.push(artifact('AUTHORITATIVE_SOURCE', 'REST', 'CODE_DECLARATIONS', [producer, ...inputs],
      ['Package script invokes a local writer', 'Writer serializes an imported OpenAPI builder to a literal output path'], {
        architecture: 'CODE_FIRST', framework, confidence: 'SUPPORTED_BY_REPOSITORY',
        generator: { tool: 'repository-script', entryPoints, outputPaths, commands },
        synchronization: 'Update the OpenAPI builder or its declarations and use the existing package scripts to regenerate and check the output.',
      }))
  }
  const presentation = findViewers(records, fileSet)
  const documents = otherDocumentation(records)
  const typeSpecOutputs = new Map()
  const configuredContracts = new Map()
  for (const { file, raw } of records.filter(({ file }) => /(?:^|\/)\.?redocly\.ya?ml$/i.test(file))) {
    try {
      const config = YAML.parse(raw)
      for (const declaration of Object.values(config?.apis || {})) {
        const source = typeof declaration?.root === 'string' && localFile(file, declaration.root, fileSet)
        if (source) configuredContracts.set(source, file)
      }
    } catch {
      // An unreadable configuration cannot establish contract ownership.
    }
  }
  for (const { file, raw } of records.filter(({ file }) => path.posix.basename(file) === 'tspconfig.yaml' || path.posix.basename(file) === 'tspconfig.yml')) {
    try {
      const config = YAML.parse(raw)
      const options = config?.options?.['@typespec/openapi3']
      if (!Array.isArray(config?.emit) || !config.emit.includes('@typespec/openapi3') || typeof options?.['output-file'] !== 'string') continue
      const outputDir = options['emitter-output-dir'] || config['output-dir']
      if (typeof outputDir !== 'string') continue
      const output = localFile(file, `${outputDir}/${options['output-file']}`, fileSet)
      if (!output) continue
      typeSpecOutputs.set(output, file)
      for (const source of documents.filter(({ type, paths }) => type === 'TYPESPEC' && path.posix.dirname(paths[0]) === path.posix.dirname(file))) {
        source.generator = { tool: '@typespec/openapi3', configuration: file, outputPaths: [output] }
        source.confidence = 'SUPPORTED_BY_REPOSITORY'
      }
    } catch {
      // Only a readable, explicit emitter configuration establishes output ownership.
    }
  }
  const generatedArtifacts = []
  const unresolvedReferences = []
  for (const spec of specs) {
    const { file, raw, generated, protocol, format, references } = spec
    const generation = commands.find(({ base, value }) => /\b(?:swagger-jsdoc|redocly\s+bundle|swagger-cli\s+bundle|spectacular)\b/.test(value)
      && Array.from(value.matchAll(/(?:^|\s)(?:--output(?:[=\s])|-o\s+|--file\s+)["']?([\w./-]+)/g))
        .some(([, output]) => localFile(base, output, fileSet) === file))
    const localReferences = [...new Set(references.map((ref) => localFile(file, ref, fileSet)).filter(Boolean))]
    if (references.length && references.some((ref) => !localFile(file, ref, fileSet) && !/^https?:\/\//.test(ref))) unresolvedReferences.push(file)
    const typeSpecConfig = typeSpecOutputs.get(file)
    const workflow = workflowByOutput.get(file)
    const isGenerated = generated || GENERATED.test(raw) || Boolean(generation) || Boolean(typeSpecConfig) || Boolean(workflow)
    const configuration = configuredContracts.get(file)
    const entry = artifact(isGenerated ? 'GENERATED_ARTIFACT' : 'AUTHORITATIVE_SOURCE', protocol, format, [file, ...localReferences],
      [isGenerated ? 'Generated marker or declared command output' : 'Structured API contract root',
        ...(configuration ? [`Declared contract input: ${configuration}`] : []), ...localReferences.map((ref) => `Local reference: ${ref}`)], {
        architecture: 'CONTRACT_FIRST', confidence: isGenerated || configuration ? 'SUPPORTED_BY_REPOSITORY' : 'CANDIDATE',
        ...(configuration ? { configuration } : {}),
        ...(generation ? { generator: { commands: [commandLocation(generation)] } } : {}),
        ...(typeSpecConfig ? { generator: { tool: '@typespec/openapi3', configuration: typeSpecConfig } } : {}),
        ...(workflow ? { generator: { tool: 'repository-script', entryPoints: workflow.entryPoints, commands: workflow.commands } } : {}),
      })
    if (isGenerated) generatedArtifacts.push(entry)
    else documents.push(entry)
  }
  for (const [file, workflow] of workflowByOutput) {
    if (specs.some((spec) => spec.file === file)) continue
    const present = inspectOutput(root, file)
    generatedArtifacts.push(artifact('GENERATED_ARTIFACT', 'REST', 'OPENAPI', [file], ['Literal output of the repository generator'], {
      present, confidence: 'SUPPORTED_BY_REPOSITORY',
      generator: { tool: 'repository-script', entryPoints: workflow.entryPoints, commands: workflow.commands },
    }))
  }
  const sourceRecords = new Map(records.map(({ file, code }) => [file, code]))
  for (const viewer of presentation) {
    const target = viewer.consumes.target
    if (target && viewer.consumes.kind === 'URL_OR_PATH' && (systems.some(({ outputEndpoints }) => outputEndpoints?.includes(target))
      || workflows.some((workflow) => servesRepositoryGenerator(viewer.paths[0], target, workflow, sourceRecords)))) {
      viewer.consumes.kind = 'GENERATOR_ENDPOINT'
    }
    if (viewer.consumes.kind === 'UNRESOLVED' && viewer.type === 'Swagger UI'
      && records.some(({ file, code }) => file === viewer.paths[0] && consumesNestGenerator(code))
      && systems.some(({ framework, generator }) => framework === 'nestjs' && generator.entryPoints.includes(viewer.paths[0]))) {
      viewer.consumes = { kind: 'IN_PROCESS_GENERATOR', target: viewer.paths[0] }
    }
  }
  generatedArtifacts.push(...documents.filter(({ role }) => role === 'GENERATED_ARTIFACT'))
  const clientCollections = Object.entries(collections).flatMap(([format, entries]) => entries.map((entry) =>
    artifact('CLIENT_COLLECTION', format === 'httpFiles' ? 'HTTP' : 'UNVERIFIED', format, [relativePath(root, entry.path || entry)], ['Existing client artifact marker'])))
  const discovered = [...systems, ...documents.filter(({ role }) => role !== 'GENERATED_ARTIFACT')]
  const protocols = [...new Set([...discovered, ...presentation, ...generatedArtifacts].map(({ protocol }) => protocol))].sort()
  const conflicts = []
  for (const protocol of protocols) {
    const candidates = discovered.filter((entry) => entry.protocol === protocol && entry.role === 'AUTHORITATIVE_SOURCE')
    if (candidates.length > 1) {
      candidates.forEach((item) => { item.role = 'UNKNOWN'; item.confidence = 'AMBIGUOUS' })
      conflicts.push({ protocol, reason: 'Multiple candidate sources without a verified ownership relationship', paths: candidates.flatMap(({ paths }) => paths) })
    }
  }
  const requestedProtocol = (targetProtocol || selection?.protocol || '').toUpperCase()
  const applies = ({ protocol }) => !requestedProtocol || requestedProtocol === protocol
  const scoped = discovered.filter(applies)
  const scopedConflicts = conflicts.filter(applies)
  const authorities = scoped.filter(({ role }) => role === 'AUTHORITATIVE_SOURCE')
  const ambiguous = coverage.incomplete || scopedConflicts.length > 0 ||
    specs.some(({ protocol, file }) => applies({ protocol }) && unresolvedReferences.includes(file))
  const status = [...scoped, ...presentation.filter(applies), ...generatedArtifacts.filter(applies)].length
    ? 'FOUND' : coverage.incomplete ? 'INCOMPLETE' : 'NOT_FOUND'
  const markdownOnly = scoped.some(({ type }) => type === 'MARKDOWN_API_REFERENCE')
    && scoped.every(({ type }) => type === 'MARKDOWN_API_REFERENCE')
    && ![...presentation, ...generatedArtifacts].some(applies)
  const explicit = selection && ['protocol', 'format', 'location', 'approach'].every((key) => typeof selection[key] === 'string' && selection[key].trim())
  const proposedCompatibility = selectionCompatibility(root, selection)
  const decision = documentationDecision({ ambiguous, authorities, markdownOnly, selection: explicit, status, compatibility: proposedCompatibility })
  const architecture = authorities.length > 1 ? 'HYBRID' : authorities[0]?.architecture || (markdownOnly ? 'DOCUMENTATION_FIRST' : 'UNVERIFIED')
  const sourceOfTruth = authorities.length === 1 && !ambiguous ? {
    type: authorities[0].type, paths: authorities[0].paths,
    verified: authorities[0].confidence === 'SUPPORTED_BY_REPOSITORY',
  } : null
  return {
    status, architecture, framework: sourceOfTruth ? authorities[0].framework || null : null, protocols, sourceOfTruth,
    targetProtocol: requestedProtocol || null,
    systems: discovered, presentation, generatedArtifacts, clientCollections, dependencyHints, conflicts, unresolvedReferences,
    compatibility: scopedConflicts.length ? 'CONFLICT_REQUIRES_DECISION'
      : status === 'NOT_FOUND' ? proposedCompatibility : coverage.incomplete || decision === 'VERIFY_OWNERSHIP' ? 'UNKNOWN' : 'PARTIALLY_COMPATIBLE',
    decision, requiresUserDecision: ['ASK_FOR_DOCUMENTATION_CHOICE', 'REVIEW_INCOMPATIBLE_SELECTION'].includes(decision) || scopedConflicts.length > 0,
    coverage,
  }
}
