#!/usr/bin/env node
/**
 * Shadow Handoff MCP Server (shadow-handoff-mcp v1.0.0)
 * Cross-agent (Antigravity, Claude Code, Codex, Gemini CLI) Context Compaction & Session Handoff MCP.
 *
 * Allows seamless session handoff when context/memory is full — even when switching between
 * Claude Code -> Antigravity -> Codex -> Gemini CLI on the same project!
 *
 * Tools:
 * 1. save_handoff: Compacts current session state (Goal, Completed, Active Contracts, Pending Tasks,
 *    Key Decisions, Blockers, File Paths) + auto-captures read-only Git status/diff-stat into
 *    ~/.shadow-handoff/projects/<project-slug>/latest.md & history/ (and optionally <project>/.handoff/HANDOFF.md).
 * 2. load_handoff: Loads the latest (or specific) handoff snapshot for a project so a fresh session
 *    resumes immediately with minimal token usage.
 * 3. list_handoffs: Lists all projects with saved handoffs or the handoff history for a specific project.
 * 4. merge_handoffs: Combines parallel sessions saved under different sessionLabels (e.g. "plan" + "review")
 *    into one handoff, keeping the lowest readiness level and the union of untested surfaces.
 *
 * Every save also records verification state (readinessLevel, untestedSurfaces, claimEvidenceMap) so
 * gaps in verification travel with the handoff instead of only the completed work.
 */

import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import readline from 'node:readline'
import { execFileSync } from 'node:child_process'

const PROTOCOL_VERSION = '2024-11-05'
const SERVER_INFO = {
  name: 'shadow-handoff-mcp',
  version: '1.1.0',
}

const HANDOFF_ROOT = path.join(os.homedir(), '.shadow-handoff')
const MAX_HISTORY_PER_PROJECT = 15
// PLANNED covers sessions that produced only a plan; the remaining levels follow the Rigor Protocol.
const READINESS_LEVELS = ['PLANNED', 'IMPLEMENTED', 'VERIFIED-LOCAL', 'REVIEWED', 'READY-TO-MERGE']
const DEFAULT_SESSION_LABEL = 'default'
const STALE_SESSION_GAP_MS = 24 * 60 * 60 * 1000

const TOOLS = [
  {
    name: 'save_handoff',
    description:
      'Create a high-density session handoff summary when context/memory is getting full or before switching AI agents (e.g. Claude -> Antigravity -> Codex). Automatically captures read-only Git branch/status/diff-stat and stores the handoff in ~/.shadow-handoff/projects/<project>/latest.md (plus optional .handoff/HANDOFF.md in the project).',
    inputSchema: {
      type: 'object',
      properties: {
        projectPath: {
          type: 'string',
          description: 'Absolute path to the active project/workspace directory',
        },
        sourceAgent: {
          type: 'string',
          description: 'Name of the current agent saving the handoff (e.g. Antigravity, Claude Code, Codex, Gemini CLI)',
        },
        title: {
          type: 'string',
          description: 'Short title of the current task or milestone',
        },
        currentGoal: {
          type: 'string',
          description: 'Primary objective the Monarch requested in this session',
        },
        completedWork: {
          type: 'array',
          items: { type: 'string' },
          description: 'Concise bullet points of work completed and verified so far',
        },
        nextSteps: {
          type: 'array',
          items: { type: 'string' },
          description: 'Ordered, actionable next steps for the next session/agent to execute immediately',
        },
        keyDecisionsAndContracts: {
          type: 'array',
          items: { type: 'string' },
          description: 'Important architectural decisions, API/DB contracts, strict types, or constraints established',
        },
        blockersOrBugs: {
          type: 'array',
          items: { type: 'string' },
          description: 'Any open bugs, failing tests, or unresolved blockers (empty if none)',
        },
        importantFiles: {
          type: 'array',
          items: { type: 'string' },
          description: 'Key file paths (with optional line ranges) that the next session should inspect first',
        },
        resumeCommandOrHint: {
          type: 'string',
          description: 'Optional command to run or exact file/function to start editing in the next session',
        },
        alsoWriteToProjectFolder: {
          type: 'boolean',
          description: 'If true, also writes a copy to <projectPath>/.handoff/HANDOFF.md (default: false to keep repo clean unless requested)',
        },
        sessionLabel: {
          type: 'string',
          description: 'Label for this session when several run in parallel on the same project (e.g. "plan", "review"). Each label keeps its own snapshot so merge_handoffs can combine them. Default: "default".',
        },
        readinessLevel: {
          type: 'string',
          enum: READINESS_LEVELS,
          description: 'Verified state of the work: PLANNED (plan only) -> IMPLEMENTED (code written) -> VERIFIED-LOCAL (probes + tests executed) -> REVIEWED (independent adversarial pass, findings resolved) -> READY-TO-MERGE.',
        },
        untestedSurfaces: {
          type: 'array',
          items: { type: 'string' },
          description: 'Surfaces NOT yet tested (e.g. "real multi-turn conversation", "topic switch", "ALL-CAPS input", "UI during streaming"). The next session must read these before concluding. Use [] only if every surface was tested.',
        },
        claimEvidenceMap: {
          type: 'array',
          items: {
            type: 'object',
            properties: {
              claim: { type: 'string', description: 'Readiness claim, e.g. "follow-up resolution is safe"' },
              evidence: { type: 'string', description: 'Evidence that measures this specific claim' },
              notMeasured: { type: 'string', description: 'What this evidence does not measure' },
            },
            required: ['claim', 'evidence'],
          },
          description: 'Claim -> evidence -> what is not measured, for every readiness claim made.',
        },
      },
      required: ['projectPath', 'title', 'currentGoal', 'completedWork', 'nextSteps', 'readinessLevel', 'untestedSurfaces'],
    },
  },
  {
    name: 'load_handoff',
    description:
      'Load the latest session handoff summary for a project (or the most recently updated project globally if projectPath is omitted) to resume work in a fresh chat session with minimal token overhead.',
    inputSchema: {
      type: 'object',
      properties: {
        projectPath: {
          type: 'string',
          description: 'Optional absolute path to the project directory. If omitted, loads the most recent handoff across all projects.',
        },
        handoffId: {
          type: 'string',
          description: 'Optional specific history filename/ID if loading an older snapshot instead of latest.',
        },
      },
    },
  },
  {
    name: 'list_handoffs',
    description:
      'List all saved project handoffs across the machine, or list the snapshot history for a specific projectPath.',
    inputSchema: {
      type: 'object',
      properties: {
        projectPath: {
          type: 'string',
          description: 'Optional project path to list its history snapshots',
        },
      },
    },
  },
  {
    name: 'merge_handoffs',
    description:
      'Combine parallel sessions on the same project (each saved with save_handoff and a distinct sessionLabel, e.g. "plan" and "review") into one handoff that a single agent can load. Keeps the LOWEST readiness level, the union of untested surfaces, label-tagged work/steps/decisions, and warns when sessions saw different branches or commits. The merged result becomes the project latest handoff.',
    inputSchema: {
      type: 'object',
      properties: {
        projectPath: {
          type: 'string',
          description: 'Absolute path to the project directory',
        },
        sessionLabels: {
          type: 'array',
          items: { type: 'string' },
          description: 'Labels to merge, in the order their nextSteps should run (e.g. ["plan", "review"]). Default: all saved sessions, oldest first.',
        },
        title: {
          type: 'string',
          description: 'Optional title for the merged handoff',
        },
        currentGoal: {
          type: 'string',
          description: 'Optional combined goal. Default: each session goal tagged with its label.',
        },
        sourceAgent: {
          type: 'string',
          description: 'Agent performing the merge',
        },
        archiveSessionsAfterMerge: {
          type: 'boolean',
          description: 'Move merged session snapshots to sessions/archive/ so a later merge does not pick them up again (default: true). Nothing is deleted.',
        },
        alsoWriteToProjectFolder: {
          type: 'boolean',
          description: 'If true, also writes the merged handoff to <projectPath>/.handoff/HANDOFF.md',
        },
      },
      required: ['projectPath'],
    },
  },
]

function resolveCanonicalProjectRoot(projectPath) {
  const abs = path.resolve(projectPath)
  try {
    if (fs.existsSync(abs)) {
      const gitTopLevel = execFileSync('git', ['-C', abs, 'rev-parse', '--show-toplevel'], {
        encoding: 'utf8',
        timeout: 2500,
        stdio: ['ignore', 'pipe', 'ignore'],
      }).trim()
      if (gitTopLevel) {
        return path.resolve(gitTopLevel)
      }
    }
  } catch {
    // Not a git repo or git unavailable; use resolved path directly
  }
  return abs
}

function projectSlugFromPath(projectPath) {
  const normalized = resolveCanonicalProjectRoot(projectPath)
  const base = path.basename(normalized)
  const parent = path.basename(path.dirname(normalized))
  const combined = `${parent}-${base}`
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
  let hash = 0
  for (let i = 0; i < normalized.length; i++) {
    hash = (hash * 31 + normalized.toLowerCase().charCodeAt(i)) >>> 0
  }
  return `${combined || 'workspace'}-${hash.toString(16).slice(0, 6)}`
}

function requireString(value, field) {
  if (typeof value !== 'string' || value.trim() === '') {
    throw new Error(`${field} is required and must be a non-empty string`)
  }
  return value.trim()
}

function sanitizeSessionLabel(label) {
  if (label === undefined || label === null || label === '') return DEFAULT_SESSION_LABEL
  if (typeof label !== 'string') throw new Error('sessionLabel must be a string')
  const clean = label
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 40)
  if (!clean) {
    throw new Error(`sessionLabel "${label}" has no usable characters (use letters or digits, e.g. "plan", "review")`)
  }
  return clean
}

function toStringArray(value, field) {
  if (value === undefined || value === null) return []
  if (!Array.isArray(value)) throw new Error(`${field} must be an array of strings`)
  return value
    .map((item, idx) => {
      if (typeof item !== 'string') throw new Error(`${field}[${idx}] must be a string`)
      return item.trim()
    })
    .filter((item) => item.length > 0)
}

function parseReadinessLevel(value) {
  if (typeof value !== 'string' || !READINESS_LEVELS.includes(value)) {
    throw new Error(`readinessLevel is required and must be one of: ${READINESS_LEVELS.join(' | ')}`)
  }
  return value
}

function parseClaimEvidenceMap(value) {
  if (value === undefined || value === null) return []
  if (!Array.isArray(value)) {
    throw new Error('claimEvidenceMap must be an array of { claim, evidence, notMeasured }')
  }
  return value.map((entry, idx) => {
    if (!entry || typeof entry !== 'object' || Array.isArray(entry)) {
      throw new Error(`claimEvidenceMap[${idx}] must be an object { claim, evidence, notMeasured }`)
    }
    const claim = requireString(entry.claim, `claimEvidenceMap[${idx}].claim`)
    const evidence = requireString(entry.evidence, `claimEvidenceMap[${idx}].evidence`)
    if (entry.notMeasured !== undefined && typeof entry.notMeasured !== 'string') {
      throw new Error(`claimEvidenceMap[${idx}].notMeasured must be a string`)
    }
    return { claim, evidence, notMeasured: (entry.notMeasured || '').trim() }
  })
}

function lowestReadiness(levels) {
  return levels.reduce((low, level) =>
    READINESS_LEVELS.indexOf(level) < READINESS_LEVELS.indexOf(low) ? level : low,
  )
}

function buildHandoffId(iso, label) {
  return `handoff-${iso.replace(/[:.]/g, '-').slice(0, 19)}-${label}`
}

function listSessionLabels(projectDir) {
  const sessionsDir = path.join(projectDir, 'sessions')
  if (!fs.existsSync(sessionsDir)) return []
  return fs
    .readdirSync(sessionsDir)
    .filter((f) => f.endsWith('.json'))
    .map((f) => f.replace(/\.json$/, ''))
    .sort()
}

// Verification state stored next to a latest.md, so loaders see readiness and gaps without parsing markdown.
function readVerificationState(latestMdPath) {
  const jsonPath = path.join(path.dirname(latestMdPath), 'latest.json')
  if (!fs.existsSync(jsonPath)) return {}
  try {
    const meta = JSON.parse(fs.readFileSync(jsonPath, 'utf8'))
    if (!meta.readinessLevel) return {}
    const pending = listSessionLabels(path.dirname(latestMdPath))
    return {
      readinessLevel: meta.readinessLevel,
      untestedSurfaces: Array.isArray(meta.untestedSurfaces) ? meta.untestedSurfaces : [],
      reviewGate:
        'Read untestedSurfaces before writing any review conclusion or readiness claim. Surfaces listed there are unverified.',
      ...(pending.length >= 2
        ? {
            unmergedSessions: pending,
            mergeHint: `Parallel sessions are saved but not merged (${pending.join(', ')}). This snapshot shows only one of them; call merge_handoffs to combine.`,
          }
        : {}),
    }
  } catch {
    return {}
  }
}

function captureGitSnapshot(projectPath) {
  try {
    if (!fs.existsSync(projectPath)) return null
    const branch = execFileSync('git', ['-C', projectPath, 'rev-parse', '--abbrev-ref', 'HEAD'], {
      encoding: 'utf8',
      timeout: 3000,
      stdio: ['ignore', 'pipe', 'ignore'],
    }).trim()
    const status = execFileSync('git', ['-C', projectPath, 'status', '-s'], {
      encoding: 'utf8',
      timeout: 3000,
      stdio: ['ignore', 'pipe', 'ignore'],
    }).trim()
    const diffStat = execFileSync('git', ['-C', projectPath, 'diff', '--stat'], {
      encoding: 'utf8',
      timeout: 3000,
      stdio: ['ignore', 'pipe', 'ignore'],
    }).trim()
    const lastCommit = execFileSync('git', ['-C', projectPath, 'log', '-n', '1', '--oneline'], {
      encoding: 'utf8',
      timeout: 3000,
      stdio: ['ignore', 'pipe', 'ignore'],
    }).trim()
    return { branch, lastCommit, status, diffStat }
  } catch {
    return null
  }
}

function formatVerificationSection(meta) {
  if (!meta.readinessLevel) return []
  const lines = [
    `## 0. Verification State (Read Before Concluding)`,
    `- **Readiness Level**: \`${meta.readinessLevel}\``,
    `- **Untested Surfaces** (unverified; do not claim these as safe):`,
    ...(meta.untestedSurfaces.length > 0
      ? meta.untestedSurfaces.map((item) => `  - [ ] ${item}`)
      : ['  - (None declared: the saving agent states every surface was tested)']),
  ]
  if (meta.claimEvidenceMap.length > 0) {
    lines.push(
      ``,
      `| Claim | Evidence | Not measured |`,
      `|---|---|---|`,
      ...meta.claimEvidenceMap.map(
        (row) =>
          `| ${row.claim.replace(/\|/g, '\\|')} | ${row.evidence.replace(/\|/g, '\\|')} | ${(row.notMeasured || '(not stated)').replace(/\|/g, '\\|')} |`,
      ),
    )
  }
  if (meta.mergeWarnings && meta.mergeWarnings.length > 0) {
    lines.push(``, `**Merge warnings:**`, ...meta.mergeWarnings.map((w) => `- ${w}`))
  }
  lines.push(``)
  return lines
}

function formatMarkdownHandoff(meta, gitInfo) {
  const lines = [
    `# SHADOW HANDOFF: ${meta.title}`,
    ``,
    `- **Project Path**: \`${meta.projectPath}\``,
    `- **Timestamp**: ${meta.createdAt}`,
    `- **Source Agent**: ${meta.sourceAgent || 'Shadow Army'}`,
    ...(meta.sessionLabel ? [`- **Session**: \`${meta.sessionLabel}\``] : []),
    ...(meta.mergedFrom && meta.mergedFrom.length > 0
      ? [`- **Merged From Sessions**: ${meta.mergedFrom.map((l) => `\`${l}\``).join(', ')}`]
      : []),
    ...(gitInfo
      ? [
          `- **Git Branch**: \`${gitInfo.branch}\` (Last commit: \`${gitInfo.lastCommit}\`)`,
        ]
      : []),
    ``,
    ...formatVerificationSection(meta),
    `## 1. Current Goal (Titah Monarch)`,
    meta.currentGoal,
    ``,
    `## 2. Completed & Verified Work`,
    ...(meta.completedWork && meta.completedWork.length > 0
      ? meta.completedWork.map((item) => `- [x] ${item}`)
      : ['- (None recorded)']),
    ``,
    `## 3. Next Exact Steps (Prioritized)`,
    ...(meta.nextSteps && meta.nextSteps.length > 0
      ? meta.nextSteps.map((item, idx) => `${idx + 1}. [ ] ${item}`)
      : ['1. [ ] Ask Monarch for next objective']),
    ``,
  ]

  if (meta.keyDecisionsAndContracts && meta.keyDecisionsAndContracts.length > 0) {
    lines.push(
      `## 4. Active Contracts, Strict Types & Key Decisions`,
      ...meta.keyDecisionsAndContracts.map((item) => `- ${item}`),
      ``,
    )
  }

  if (meta.blockersOrBugs && meta.blockersOrBugs.length > 0) {
    lines.push(
      `## 5. Open Blockers / Bugs`,
      ...meta.blockersOrBugs.map((item) => `- ⚠️ ${item}`),
      ``,
    )
  }

  if (meta.importantFiles && meta.importantFiles.length > 0) {
    lines.push(
      `## 6. Key Files to Scout First`,
      ...meta.importantFiles.map((f) => `- \`${f}\``),
      ``,
    )
  }

  if (meta.resumeCommandOrHint) {
    lines.push(`## 7. Immediate Resume Hint`, `\`${meta.resumeCommandOrHint}\``, ``)
  }

  if (gitInfo && (gitInfo.status || gitInfo.diffStat)) {
    lines.push(`## 8. Uncommitted Git State (Auto-Captured)`)
    if (gitInfo.status) {
      lines.push('```text', gitInfo.status, '```')
    }
    if (gitInfo.diffStat) {
      lines.push('```text', gitInfo.diffStat, '```')
    }
    lines.push('')
  }

  return lines.join('\n')
}

function handleSaveHandoff(args) {
  const projectPathArg = requireString(args.projectPath, 'projectPath')
  const resolvedProjectPath = resolveCanonicalProjectRoot(projectPathArg)
  const slug = projectSlugFromPath(resolvedProjectPath)
  const projectDir = path.join(HANDOFF_ROOT, 'projects', slug)
  const sessionLabel = sanitizeSessionLabel(args.sessionLabel)
  const iso = new Date().toISOString()

  const gitInfo = captureGitSnapshot(resolvedProjectPath)
  const meta = {
    handoffId: buildHandoffId(iso, sessionLabel),
    projectSlug: slug,
    projectPath: resolvedProjectPath,
    sourceAgent: args.sourceAgent || 'Shadow Army',
    sessionLabel,
    title: requireString(args.title, 'title'),
    currentGoal: requireString(args.currentGoal, 'currentGoal'),
    completedWork: toStringArray(args.completedWork, 'completedWork'),
    nextSteps: toStringArray(args.nextSteps, 'nextSteps'),
    keyDecisionsAndContracts: toStringArray(args.keyDecisionsAndContracts, 'keyDecisionsAndContracts'),
    blockersOrBugs: toStringArray(args.blockersOrBugs, 'blockersOrBugs'),
    importantFiles: toStringArray(args.importantFiles, 'importantFiles'),
    resumeCommandOrHint: typeof args.resumeCommandOrHint === 'string' ? args.resumeCommandOrHint : '',
    readinessLevel: parseReadinessLevel(args.readinessLevel),
    untestedSurfaces: (() => {
      if (!Array.isArray(args.untestedSurfaces)) {
        throw new Error('untestedSurfaces is required: list surfaces not yet tested, or [] if every surface was tested')
      }
      return toStringArray(args.untestedSurfaces, 'untestedSurfaces')
    })(),
    claimEvidenceMap: parseClaimEvidenceMap(args.claimEvidenceMap),
    createdAt: iso,
    git: gitInfo,
  }

  const written = writeHandoffFiles(meta, gitInfo, args.alsoWriteToProjectFolder === true)

  // Per-session snapshot: a parallel session saving under another label no longer erases this one.
  const sessionsDir = path.join(projectDir, 'sessions')
  fs.mkdirSync(sessionsDir, { recursive: true })
  fs.writeFileSync(path.join(sessionsDir, `${sessionLabel}.json`), JSON.stringify(meta, null, 2) + '\n', 'utf8')

  const otherSessions = listSessionLabels(projectDir).filter((label) => label !== sessionLabel)

  return {
    status: 'saved',
    handoffId: meta.handoffId,
    projectSlug: slug,
    projectPath: resolvedProjectPath,
    sessionLabel,
    readinessLevel: meta.readinessLevel,
    untestedSurfacesCount: meta.untestedSurfaces.length,
    latestMdPath: written.latestMdPath,
    ...(written.projectCopyPath ? { projectCopyPath: written.projectCopyPath } : {}),
    nextStepsCount: meta.nextSteps.length,
    gitCaptured: Boolean(gitInfo),
    ...(otherSessions.length > 0
      ? {
          parallelSessions: otherSessions,
          mergeHint: `Other sessions are saved for this project (${otherSessions.join(', ')}). latest.md now shows only "${sessionLabel}". Call merge_handoffs to combine them before switching to one agent.`,
        }
      : {}),
    resumeInstruction:
      'In any new session (Antigravity, Claude Code, Codex, or Gemini CLI), say "lanjut handoff" to load this snapshot immediately.',
  }
}

function writeHandoffFiles(meta, gitInfo, alsoWriteToProjectFolder) {
  const projectDir = path.join(HANDOFF_ROOT, 'projects', meta.projectSlug)
  const historyDir = path.join(projectDir, 'history')
  fs.mkdirSync(historyDir, { recursive: true })
  const handoffId = meta.handoffId
  const slug = meta.projectSlug
  const resolvedProjectPath = meta.projectPath
  const iso = meta.createdAt

  const markdown = formatMarkdownHandoff(meta, gitInfo)
  const latestMdPath = path.join(projectDir, 'latest.md')
  const latestJsonPath = path.join(projectDir, 'latest.json')
  const historyMdPath = path.join(historyDir, `${handoffId}.md`)

  fs.writeFileSync(latestMdPath, markdown, 'utf8')
  fs.writeFileSync(latestJsonPath, JSON.stringify(meta, null, 2) + '\n', 'utf8')
  fs.writeFileSync(historyMdPath, markdown, 'utf8')

  // Prune old history files beyond MAX_HISTORY_PER_PROJECT
  const historyFiles = fs
    .readdirSync(historyDir)
    .filter((f) => f.endsWith('.md'))
    .sort()
  while (historyFiles.length > MAX_HISTORY_PER_PROJECT) {
    const oldest = historyFiles.shift()
    if (oldest) {
      try {
        fs.unlinkSync(path.join(historyDir, oldest))
      } catch {}
    }
  }

  // Update global index.json
  const indexPath = path.join(HANDOFF_ROOT, 'index.json')
  let indexData = { projects: {} }
  if (fs.existsSync(indexPath)) {
    try {
      indexData = JSON.parse(fs.readFileSync(indexPath, 'utf8'))
    } catch {
      indexData = { projects: {} }
    }
  }
  indexData.projects[slug] = {
    projectSlug: slug,
    projectPath: resolvedProjectPath,
    latestHandoffId: handoffId,
    title: meta.title,
    sourceAgent: meta.sourceAgent,
    readinessLevel: meta.readinessLevel,
    updatedAt: iso,
    latestMdPath,
  }
  fs.writeFileSync(indexPath, JSON.stringify(indexData, null, 2) + '\n', 'utf8')

  let projectCopyPath = null
  if (alsoWriteToProjectFolder && fs.existsSync(resolvedProjectPath)) {
    projectCopyPath = path.join(resolvedProjectPath, '.handoff', 'HANDOFF.md')
    fs.mkdirSync(path.dirname(projectCopyPath), { recursive: true })
    fs.writeFileSync(projectCopyPath, markdown, 'utf8')
  }

  return { latestMdPath, projectCopyPath }
}

// Same text from several sessions collapses into one entry tagged with every label that reported it.
function unionTagged(sessions, field) {
  const order = []
  const labelsByText = new Map()
  for (const session of sessions) {
    const items = Array.isArray(session[field]) ? session[field] : []
    for (const item of items) {
      if (!labelsByText.has(item)) {
        labelsByText.set(item, [])
        order.push(item)
      }
      const labels = labelsByText.get(item)
      if (!labels.includes(session.sessionLabel)) labels.push(session.sessionLabel)
    }
  }
  return order.map((item) => `[${labelsByText.get(item).join('+')}] ${item}`)
}

function handleMergeHandoffs(args = {}) {
  const resolvedProjectPath = resolveCanonicalProjectRoot(requireString(args.projectPath, 'projectPath'))
  const slug = projectSlugFromPath(resolvedProjectPath)
  const projectDir = path.join(HANDOFF_ROOT, 'projects', slug)
  const sessionsDir = path.join(projectDir, 'sessions')
  const available = listSessionLabels(projectDir)

  const requested =
    args.sessionLabels === undefined || args.sessionLabels === null
      ? null
      : toStringArray(args.sessionLabels, 'sessionLabels').map(sanitizeSessionLabel)
  if (requested) {
    const missing = requested.filter((label) => !available.includes(label))
    if (missing.length > 0) {
      throw new Error(
        `Session(s) not found: ${missing.join(', ')}. Saved sessions for this project: ${available.join(', ') || '(none)'}`,
      )
    }
  }

  const sessions = (requested || available).map((label) =>
    JSON.parse(fs.readFileSync(path.join(sessionsDir, `${label}.json`), 'utf8')),
  )
  if (!requested) {
    sessions.sort((a, b) => String(a.createdAt).localeCompare(String(b.createdAt)))
  }
  if (sessions.length < 2) {
    throw new Error(
      `merge_handoffs needs at least 2 saved sessions; found ${sessions.length} (${available.join(', ') || 'none'}). Save each parallel session with its own sessionLabel first, or use load_handoff for a single session.`,
    )
  }

  const warnings = []
  const branches = [...new Set(sessions.map((s) => (s.git ? s.git.branch : '(no git)')))]
  if (branches.length > 1) {
    warnings.push(`Sessions were on different branches (${branches.join(', ')}). Confirm which branch the merged work targets before continuing.`)
  }
  const commits = [...new Set(sessions.map((s) => (s.git ? s.git.lastCommit : '(no git)')))]
  if (branches.length === 1 && commits.length > 1) {
    warnings.push(`Sessions saw different commits (${commits.join(' | ')}). A review may describe code that has since changed.`)
  }
  const times = sessions.map((s) => Date.parse(s.createdAt)).filter((t) => !Number.isNaN(t))
  if (times.length > 1 && Math.max(...times) - Math.min(...times) > STALE_SESSION_GAP_MS) {
    warnings.push('Sessions were saved more than 24 hours apart. Check that the older one is still current.')
  }
  const levels = sessions.map((s) => {
    if (READINESS_LEVELS.includes(s.readinessLevel)) return s.readinessLevel
    warnings.push(`Session "${s.sessionLabel}" has no readinessLevel; treated as PLANNED.`)
    return 'PLANNED'
  })
  warnings.push('Decisions and steps from different sessions are listed side by side, not reconciled. Check them for contradictions before acting.')

  const labels = sessions.map((s) => s.sessionLabel)
  const iso = new Date().toISOString()
  const gitInfo = captureGitSnapshot(resolvedProjectPath)
  const meta = {
    handoffId: buildHandoffId(iso, 'merged'),
    projectSlug: slug,
    projectPath: resolvedProjectPath,
    sourceAgent: args.sourceAgent || 'Shadow Army',
    mergedFrom: labels,
    title: typeof args.title === 'string' && args.title.trim() ? args.title.trim() : `Merged: ${sessions.map((s) => s.title).join(' + ')}`,
    currentGoal:
      typeof args.currentGoal === 'string' && args.currentGoal.trim()
        ? args.currentGoal.trim()
        : sessions.map((s) => `[${s.sessionLabel}] ${s.currentGoal}`).join('\n'),
    completedWork: sessions.flatMap((s) => s.completedWork.map((item) => `[${s.sessionLabel}] ${item}`)),
    nextSteps: sessions.flatMap((s) => s.nextSteps.map((item) => `[${s.sessionLabel}] ${item}`)),
    keyDecisionsAndContracts: unionTagged(sessions, 'keyDecisionsAndContracts'),
    blockersOrBugs: unionTagged(sessions, 'blockersOrBugs'),
    importantFiles: [...new Set(sessions.flatMap((s) => s.importantFiles))],
    resumeCommandOrHint: sessions
      .filter((s) => s.resumeCommandOrHint)
      .map((s) => `[${s.sessionLabel}] ${s.resumeCommandOrHint}`)
      .join(' ; '),
    readinessLevel: lowestReadiness(levels),
    untestedSurfaces: unionTagged(sessions, 'untestedSurfaces'),
    claimEvidenceMap: sessions.flatMap((s) =>
      (Array.isArray(s.claimEvidenceMap) ? s.claimEvidenceMap : []).map((row) => ({
        ...row,
        claim: `[${s.sessionLabel}] ${row.claim}`,
      })),
    ),
    mergeWarnings: warnings,
    createdAt: iso,
    git: gitInfo,
  }

  const written = writeHandoffFiles(meta, gitInfo, args.alsoWriteToProjectFolder === true)

  const archived = []
  if (args.archiveSessionsAfterMerge !== false) {
    const archiveDir = path.join(sessionsDir, 'archive')
    fs.mkdirSync(archiveDir, { recursive: true })
    const stamp = iso.replace(/[:.]/g, '-').slice(0, 19)
    for (const label of labels) {
      const target = path.join(archiveDir, `${label}-${stamp}.json`)
      fs.renameSync(path.join(sessionsDir, `${label}.json`), target)
      archived.push(target)
    }
  }

  return {
    status: 'merged',
    handoffId: meta.handoffId,
    projectPath: resolvedProjectPath,
    mergedFrom: labels,
    readinessLevel: meta.readinessLevel,
    untestedSurfacesCount: meta.untestedSurfaces.length,
    warnings,
    latestMdPath: written.latestMdPath,
    ...(written.projectCopyPath ? { projectCopyPath: written.projectCopyPath } : {}),
    archivedSessions: archived,
    resumeInstruction: 'Say "lanjut handoff" in the target agent to load the merged handoff.',
  }
}

function handleLoadHandoff(args = {}) {
  const indexPath = path.join(HANDOFF_ROOT, 'index.json')
  if (args.projectPath) {
    const resolvedProjectPath = resolveCanonicalProjectRoot(args.projectPath)
    const slug = projectSlugFromPath(resolvedProjectPath)
    const projectDir = path.join(HANDOFF_ROOT, 'projects', slug)

    if (args.handoffId) {
      const cleanId = args.handoffId.replace(/\.md$/, '')
      const histFile = path.join(projectDir, 'history', `${cleanId}.md`)
      if (!fs.existsSync(histFile)) {
        throw new Error(`Handoff snapshot ${cleanId} not found for ${resolvedProjectPath}`)
      }
      return {
        status: 'loaded_exact_history',
        matchedBy: 'exact_git_root_or_path',
        projectPath: resolvedProjectPath,
        handoffId: cleanId,
        markdown: fs.readFileSync(histFile, 'utf8'),
      }
    }

    const latestMdPath = path.join(projectDir, 'latest.md')
    if (fs.existsSync(latestMdPath)) {
      return {
        status: 'loaded',
        matchedBy: 'exact_git_root_or_path',
        projectPath: resolvedProjectPath,
        latestMdPath,
        ...readVerificationState(latestMdPath),
        markdown: fs.readFileSync(latestMdPath, 'utf8'),
      }
    }

    // Smart Parent / Subfolder fallback via index.json (e.g. saved in Monorepo root, opened in /backend)
    if (fs.existsSync(indexPath)) {
      try {
        const indexData = JSON.parse(fs.readFileSync(indexPath, 'utf8'))
        const reqLower = resolvedProjectPath.toLowerCase()
        const parentOrChildMatch = Object.values(indexData.projects || {})
          .filter((p) => {
            const pLower = String(p.projectPath || '').toLowerCase()
            return (
              reqLower.startsWith(pLower + path.sep) ||
              pLower.startsWith(reqLower + path.sep)
            )
          })
          .sort((a, b) => String(b.updatedAt).localeCompare(String(a.updatedAt)))[0]

        if (parentOrChildMatch && fs.existsSync(parentOrChildMatch.latestMdPath)) {
          return {
            status: 'loaded',
            matchedBy: 'parent_or_subfolder_match',
            requestedPath: resolvedProjectPath,
            projectPath: parentOrChildMatch.projectPath,
            latestMdPath: parentOrChildMatch.latestMdPath,
            ...readVerificationState(parentOrChildMatch.latestMdPath),
            markdown: fs.readFileSync(parentOrChildMatch.latestMdPath, 'utf8'),
          }
        }
      } catch {}
    }

    // Fallback: check if project has .handoff/HANDOFF.md locally
    const localHandoff = path.join(resolvedProjectPath, '.handoff', 'HANDOFF.md')
    if (fs.existsSync(localHandoff)) {
      return {
        status: 'loaded_from_project_folder',
        matchedBy: 'local_handoff_file',
        projectPath: resolvedProjectPath,
        latestMdPath: localHandoff,
        markdown: fs.readFileSync(localHandoff, 'utf8'),
      }
    }

    throw new Error(`No saved handoff found for project: ${resolvedProjectPath}`)
  }

  // No projectPath provided -> load the most recently updated project globally
  if (!fs.existsSync(indexPath)) {
    throw new Error('No handoffs have been saved yet.')
  }
  const indexData = JSON.parse(fs.readFileSync(indexPath, 'utf8'))
  const entries = Object.values(indexData.projects || {}).sort((a, b) =>
    String(b.updatedAt).localeCompare(String(a.updatedAt)),
  )
  if (entries.length === 0) {
    throw new Error('No handoffs found in index.')
  }
  const latestEntry = entries[0]
  return {
    status: 'loaded_most_recent_global',
    projectPath: latestEntry.projectPath,
    updatedAt: latestEntry.updatedAt,
    latestMdPath: latestEntry.latestMdPath,
    ...readVerificationState(latestEntry.latestMdPath),
    markdown: fs.readFileSync(latestEntry.latestMdPath, 'utf8'),
  }
}

function handleListHandoffs(args = {}) {
  if (args.projectPath) {
    const resolvedProjectPath = resolveCanonicalProjectRoot(args.projectPath)
    const slug = projectSlugFromPath(resolvedProjectPath)
    const projectDir = path.join(HANDOFF_ROOT, 'projects', slug)
    const historyDir = path.join(projectDir, 'history')
    const sessions = listSessionLabels(projectDir)
    if (!fs.existsSync(historyDir)) {
      return { projectPath: resolvedProjectPath, history: [], sessions }
    }
    const files = fs
      .readdirSync(historyDir)
      .filter((f) => f.endsWith('.md'))
      .sort()
      .reverse()
    return {
      projectPath: resolvedProjectPath,
      projectSlug: slug,
      history: files.map((f) => f.replace(/\.md$/, '')),
      sessions,
    }
  }

  const indexPath = path.join(HANDOFF_ROOT, 'index.json')
  if (!fs.existsSync(indexPath)) {
    return { projects: [] }
  }
  const indexData = JSON.parse(fs.readFileSync(indexPath, 'utf8'))
  const projects = Object.values(indexData.projects || {}).sort((a, b) =>
    String(b.updatedAt).localeCompare(String(a.updatedAt)),
  )
  return { totalProjects: projects.length, projects }
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
      if (toolName === 'save_handoff') {
        const out = handleSaveHandoff(toolArgs)
        sendToolText(id, out)
      } else if (toolName === 'load_handoff') {
        const out = handleLoadHandoff(toolArgs)
        sendToolText(id, out)
      } else if (toolName === 'list_handoffs') {
        const out = handleListHandoffs(toolArgs)
        sendToolText(id, out)
      } else if (toolName === 'merge_handoffs') {
        const out = handleMergeHandoffs(toolArgs)
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
