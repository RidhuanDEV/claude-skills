import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import test from 'node:test'

import {
  handleListHandoffs,
  handleLoadHandoff,
  handleMergeHandoffs,
  handleSaveHandoff,
} from './index.mjs'

function makeTempGitRepo() {
  const repoDir = fs.mkdtempSync(path.join(os.tmpdir(), 'shadow-handoff-repo-'))
  execFileSync('git', ['init', '-b', 'main'], { cwd: repoDir, stdio: 'ignore' })
  execFileSync('git', ['config', 'user.email', 'test@shadow.local'], { cwd: repoDir, stdio: 'ignore' })
  execFileSync('git', ['config', 'user.name', 'Shadow Test'], { cwd: repoDir, stdio: 'ignore' })
  fs.writeFileSync(path.join(repoDir, 'README.md'), '# Demo\n', 'utf8')
  execFileSync('git', ['add', 'README.md'], { cwd: repoDir, stdio: 'ignore' })
  execFileSync('git', ['commit', '-m', 'init'], { cwd: repoDir, stdio: 'ignore' })
  return repoDir
}

test('C03/E15: save two parallel sessions, detect git branch/HEAD drift, merge lowest readiness and scope', () => {
  const handoffRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'shadow-handoff-store-'))
  const repoDir = makeTempGitRepo()
  const prevRoot = process.env.SHADOW_HANDOFF_ROOT
  process.env.SHADOW_HANDOFF_ROOT = handoffRoot

  try {
    const savePlan = handleSaveHandoff({
      projectPath: repoDir,
      sessionLabel: 'plan',
      title: 'API Docs & Scope Plan',
      currentGoal: 'Approve OpenAPI format and document /orders',
      completedWork: ['Discovered README-only summary'],
      nextSteps: ['Write openapi.yaml after user choice'],
      keyDecisionsAndContracts: ['User selected OpenAPI 3.1 + Scalar'],
      importantFiles: ['README.md'],
      readinessLevel: 'VERIFIED-LOCAL',
      untestedSurfaces: ['live host UI'],
      authorizationScope: {
        resource: 'apps/backend/openapi.yaml',
        host: 'localhost:3000',
        phase: 'implementation',
        operations: ['edit_docs', 'run_unit_tests'],
        explicitDecisions: ['api_docs_format=openapi3.1+scalar'],
      },
    })
    assert.equal(savePlan.status, 'saved')
    assert.equal(savePlan.gitCaptured, true)

    // Advance HEAD & switch branch before saving review session
    execFileSync('git', ['checkout', '-b', 'feat/review-check'], { cwd: repoDir, stdio: 'ignore' })
    fs.writeFileSync(path.join(repoDir, 'README.md'), '# Demo Updated\n', 'utf8')
    execFileSync('git', ['add', 'README.md'], { cwd: repoDir, stdio: 'ignore' })
    execFileSync('git', ['commit', '-m', 'update readme'], { cwd: repoDir, stdio: 'ignore' })

    const loadedAfterDrift = handleLoadHandoff({ projectPath: repoDir })
    assert.equal(loadedAfterDrift.gitDrift.detected, true)
    assert.equal(loadedAfterDrift.gitDrift.branchChanged, true)
    assert.equal(loadedAfterDrift.gitDrift.headChanged, true)
    assert.match(loadedAfterDrift.gitDrift.warning, /branch moved from "main" to "feat\/review-check"/)
    assert.deepEqual(loadedAfterDrift.authorizationScope.explicitDecisions, [
      'api_docs_format=openapi3.1+scalar',
    ])

    const saveReview = handleSaveHandoff({
      projectPath: repoDir,
      sessionLabel: 'review',
      title: 'Security Review Pass',
      currentGoal: 'Verify auth boundary before merge',
      completedWork: ['Checked RBAC matrix'],
      nextSteps: ['Add negative tenant export test'],
      keyDecisionsAndContracts: ['Keep code_review L0 read-only'],
      importantFiles: ['src/auth.ts'],
      readinessLevel: 'IMPLEMENTED',
      untestedSurfaces: ['multi-tenant export on staging'],
      authorizationScope: {
        resource: 'apps/backend/src/auth.ts',
        host: 'localhost:3000',
        phase: 'review',
        operations: ['read_only'],
        explicitDecisions: ['no_prod_touch=true'],
      },
    })
    assert.deepEqual(saveReview.parallelSessions, ['plan'])

    const merged = handleMergeHandoffs({ projectPath: repoDir })
    assert.equal(merged.status, 'merged')
    assert.equal(merged.readinessLevel, 'IMPLEMENTED')
    assert.equal(merged.untestedSurfacesCount, 2)
    assert.ok(merged.warnings.some((w) => w.includes('different branches')))
    assert.ok(merged.warnings.some((w) => w.includes('differing authorizationScope')))

    const loadedMerged = handleLoadHandoff({ projectPath: repoDir })
    assert.equal(loadedMerged.readinessLevel, 'IMPLEMENTED')
    assert.equal(loadedMerged.gitDrift.detected, false)
    assert.ok(loadedMerged.untestedSurfaces.some((s) => s.includes('[plan] live host UI')))
    assert.ok(loadedMerged.untestedSurfaces.some((s) => s.includes('[review] multi-tenant export')))
    assert.ok(
      loadedMerged.authorizationScope.explicitDecisions.includes(
        '[plan] api_docs_format=openapi3.1+scalar',
      ),
    )

    const listed = handleListHandoffs({ projectPath: repoDir })
    assert.ok(listed.history.length >= 3)
  } finally {
    if (prevRoot === undefined) delete process.env.SHADOW_HANDOFF_ROOT
    else process.env.SHADOW_HANDOFF_ROOT = prevRoot
    fs.rmSync(handoffRoot, { recursive: true, force: true })
    fs.rmSync(repoDir, { recursive: true, force: true })
  }
})

test('C03: legacy handoff without latest.json or readinessLevel is flagged as UNVERIFIED_LEGACY_SNAPSHOT', () => {
  const handoffRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'shadow-handoff-legacy-'))
  const repoDir = fs.mkdtempSync(path.join(os.tmpdir(), 'shadow-handoff-legacy-proj-'))
  const prevRoot = process.env.SHADOW_HANDOFF_ROOT
  process.env.SHADOW_HANDOFF_ROOT = handoffRoot

  try {
    const localHandoffDir = path.join(repoDir, '.handoff')
    fs.mkdirSync(localHandoffDir, { recursive: true })
    fs.writeFileSync(
      path.join(localHandoffDir, 'HANDOFF.md'),
      '# SHADOW HANDOFF: Legacy Snapshot\n\n- Old format without latest.json\n',
      'utf8',
    )

    const loaded = handleLoadHandoff({ projectPath: repoDir })
    assert.equal(loaded.status, 'loaded_from_project_folder')
    assert.equal(loaded.legacyStatus, 'UNVERIFIED_LEGACY_SNAPSHOT')
    assert.match(loaded.reviewGate, /Legacy handoff snapshot/i)
  } finally {
    if (prevRoot === undefined) delete process.env.SHADOW_HANDOFF_ROOT
    else process.env.SHADOW_HANDOFF_ROOT = prevRoot
    fs.rmSync(handoffRoot, { recursive: true, force: true })
    fs.rmSync(repoDir, { recursive: true, force: true })
  }
})
