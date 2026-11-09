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
 */

import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import readline from 'node:readline'
import { execFileSync } from 'node:child_process'

const PROTOCOL_VERSION = '2024-11-05'
const SERVER_INFO = {
  name: 'shadow-handoff-mcp',
  version: '1.0.0',
}

const HANDOFF_ROOT = path.join(os.homedir(), '.shadow-handoff')
const MAX_HISTORY_PER_PROJECT = 15

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
      },
      required: ['projectPath', 'title', 'currentGoal', 'completedWork', 'nextSteps'],
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

function formatMarkdownHandoff(meta, gitInfo) {
  const lines = [
    `# SHADOW HANDOFF: ${meta.title}`,
    ``,
    `- **Project Path**: \`${meta.projectPath}\``,
    `- **Timestamp**: ${meta.createdAt}`,
    `- **Source Agent**: ${meta.sourceAgent || 'Shadow Army'}`,
    ...(gitInfo
      ? [
          `- **Git Branch**: \`${gitInfo.branch}\` (Last commit: \`${gitInfo.lastCommit}\`)`,
        ]
      : []),
    ``,
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
  const resolvedProjectPath = resolveCanonicalProjectRoot(args.projectPath)
  const slug = projectSlugFromPath(resolvedProjectPath)
  const projectDir = path.join(HANDOFF_ROOT, 'projects', slug)
  const historyDir = path.join(projectDir, 'history')
  fs.mkdirSync(historyDir, { recursive: true })

  const now = new Date()
  const iso = now.toISOString()
  const stamp = iso.replace(/[:.]/g, '-').slice(0, 19)
  const handoffId = `handoff-${stamp}`

  const gitInfo = captureGitSnapshot(resolvedProjectPath)
  const meta = {
    handoffId,
    projectSlug: slug,
    projectPath: resolvedProjectPath,
    sourceAgent: args.sourceAgent || 'Shadow Army',
    title: args.title,
    currentGoal: args.currentGoal,
    completedWork: args.completedWork || [],
    nextSteps: args.nextSteps || [],
    keyDecisionsAndContracts: args.keyDecisionsAndContracts || [],
    blockersOrBugs: args.blockersOrBugs || [],
    importantFiles: args.importantFiles || [],
    resumeCommandOrHint: args.resumeCommandOrHint || '',
    createdAt: iso,
    git: gitInfo,
  }

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
    title: args.title,
    sourceAgent: meta.sourceAgent,
    updatedAt: iso,
    latestMdPath,
  }
  fs.writeFileSync(indexPath, JSON.stringify(indexData, null, 2) + '\n', 'utf8')

  let projectCopyPath = null
  if (args.alsoWriteToProjectFolder && fs.existsSync(resolvedProjectPath)) {
    projectCopyPath = path.join(resolvedProjectPath, '.handoff', 'HANDOFF.md')
    fs.mkdirSync(path.dirname(projectCopyPath), { recursive: true })
    fs.writeFileSync(projectCopyPath, markdown, 'utf8')
  }

  return {
    status: 'saved',
    handoffId,
    projectSlug: slug,
    projectPath: resolvedProjectPath,
    latestMdPath,
    ...(projectCopyPath ? { projectCopyPath } : {}),
    nextStepsCount: meta.nextSteps.length,
    gitCaptured: Boolean(gitInfo),
    resumeInstruction:
      'In any new session (Antigravity, Claude Code, Codex, or Gemini CLI), say "lanjut handoff" to load this snapshot immediately.',
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
    markdown: fs.readFileSync(latestEntry.latestMdPath, 'utf8'),
  }
}

function handleListHandoffs(args = {}) {
  if (args.projectPath) {
    const resolvedProjectPath = path.resolve(args.projectPath)
    const slug = projectSlugFromPath(resolvedProjectPath)
    const historyDir = path.join(HANDOFF_ROOT, 'projects', slug, 'history')
    if (!fs.existsSync(historyDir)) {
      return { projectPath: resolvedProjectPath, history: [] }
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
