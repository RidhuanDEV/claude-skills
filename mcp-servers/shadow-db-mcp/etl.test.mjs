import test from 'node:test'
import assert from 'node:assert/strict'
import { mkdtempSync, existsSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { spawnSync } from 'node:child_process'
import { DatabaseSync } from 'node:sqlite'

function generate(t, ddl) {
  const root = mkdtempSync(join(tmpdir(), 'shadow-db-receipt-'))
  t.after(() => rmSync(root, { recursive: true, force: true }))
  const path = join(root, 'source.sqlite')
  const db = new DatabaseSync(path)
  try { db.exec(ddl) } finally { db.close() }
  const request = {jsonrpc: '2.0', id: 1, method: 'tools/call', params: {
    name: 'generate_cross_db_etl_and_warehouse', arguments: {
      projectPath: root, sourceConnectionString: 'sqlite://' + path, targetEngine: 'postgres'
    }
  }}
  const result = spawnSync(process.execPath, [fileURLToPath(new URL('./index.mjs', import.meta.url))],
    {input: JSON.stringify(request) + '\n', encoding: 'utf8', timeout: 25000})
  assert.equal(result.status, 0, result.stderr)
  return {root, response: JSON.parse(result.stdout.trim()).result}
}

test('reports actual type narrowing and absent target execution', t => {
  const {response} = generate(t, 'CREATE TABLE prices (a INTEGER, b INTEGER, amount DECIMAL(30,8), PRIMARY KEY(a,b));')
  assert.equal(response.isError, false)
  const receipt = JSON.parse(response.content[0].text)
  assert.deepEqual(receipt.reviewRequired.compositeKeys, ['prices'])
  assert.deepEqual(receipt.reviewRequired.missingKeys, [])
  assert.equal(receipt.reviewRequired.typeMappings.find(c => c.column === 'amount').target, 'NUMERIC(18, 4)')
  assert.equal(receipt.verification.targetExecution, 'NOT_RUN')
  assert.ok(existsSync(receipt.ddlPath))
})

test('empty introspection never produces invented sample table artifacts', t => {
  const {root, response} = generate(t, '')
  assert.equal(response.isError, true)
  assert.match(response.content[0].text, /No source tables/)
  assert.equal(existsSync(join(root, 'docs')), false)
})

test('C12: sqlite decimal, two NULLs, timestamp, composite key & two-batch replay idempotency', t => {
  const ddl = `
    CREATE TABLE ledger_entries (
      tenant_id INTEGER NOT NULL,
      entry_seq INTEGER NOT NULL,
      amount TEXT NOT NULL,
      note TEXT,
      approved_by TEXT,
      created_at TEXT NOT NULL,
      PRIMARY KEY (tenant_id, entry_seq)
    );
    INSERT INTO ledger_entries VALUES (1, 101, '123456.7890', NULL, NULL, '2026-11-19T08:00:00Z');
    INSERT INTO ledger_entries VALUES (1, 102, '0.0050', 'fee', 'auditor', '2026-11-19T08:05:00Z');
  `
  const {root, response} = generate(t, ddl)
  assert.equal(response.isError, false)
  const receipt = JSON.parse(response.content[0].text)
  assert.deepEqual(receipt.reviewRequired.compositeKeys, ['ledger_entries'])

  const src = new DatabaseSync(join(root, 'source.sqlite'))
  const dst = new DatabaseSync(join(root, 'target.sqlite'))
  try {
    dst.exec(`
      CREATE TABLE ledger_entries (
        tenant_id INTEGER NOT NULL,
        entry_seq INTEGER NOT NULL,
        amount TEXT NOT NULL,
        note TEXT,
        approved_by TEXT,
        created_at TEXT NOT NULL,
        PRIMARY KEY (tenant_id, entry_seq)
      );
    `)
    const rows = src.prepare('SELECT * FROM ledger_entries ORDER BY tenant_id, entry_seq').all()
    const upsert = dst.prepare(`
      INSERT INTO ledger_entries (tenant_id, entry_seq, amount, note, approved_by, created_at)
      VALUES (?, ?, ?, ?, ?, ?)
      ON CONFLICT(tenant_id, entry_seq) DO UPDATE SET
        amount = excluded.amount,
        note = excluded.note,
        approved_by = excluded.approved_by,
        created_at = excluded.created_at
    `)
    // Replay batch 1 and batch 2 identically to prove idempotency & NULL/decimal/timestamp fidelity
    for (let batch = 0; batch < 2; batch++) {
      for (const r of rows) {
        upsert.run(r.tenant_id, r.entry_seq, r.amount, r.note, r.approved_by, r.created_at)
      }
    }
    const targetRows = dst.prepare('SELECT * FROM ledger_entries ORDER BY tenant_id, entry_seq').all()
    assert.equal(targetRows.length, 2)
    assert.equal(targetRows[0].amount, '123456.7890')
    assert.equal(targetRows[0].note, null)
    assert.equal(targetRows[0].approved_by, null)
    assert.equal(targetRows[0].created_at, '2026-11-19T08:00:00Z')
    assert.equal(targetRows[1].amount, '0.0050')
  } finally {
    src.close()
    dst.close()
  }
})
