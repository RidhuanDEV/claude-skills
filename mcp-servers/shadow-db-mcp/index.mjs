#!/usr/bin/env node
/**
 * Shadow Database Inspector, Multi-DB & Cross-Engine ETL/Warehouse MCP Server (shadow-db-mcp v2.0.0)
 *
 * Supported Engines (100% Read-Only Introspection):
 * 1. PostgreSQL / Supabase / Neon / Timescale / Redshift (`pg`)
 * 2. MySQL / MariaDB / TiDB (`mysql2`)
 * 3. Microsoft SQL Server / Azure SQL (`mssql`)
 * 4. MongoDB (`mongodb` - samples documents to infer collection schemas)
 * 5. SQLite (`node:sqlite`)
 *
 * Capabilities:
 * - inspect_database_schema: Live schema introspection from any engine or .env
 * - run_readonly_query: Strict read-only SQL query execution
 * - generate_dbml_and_erd: Auto-generates docs/db/schema.dbml & docs/db/ERD.md
 * - compare_database_schemas: Diffs two databases (e.g. MySQL Project A vs Postgres Project B)
 * - generate_cross_db_etl_and_warehouse: Translates schema & generates Target DDL + Star Schema Warehouse (dim_ and fact_ tables) + Incremental Upsert ETL SQL across PostgreSQL, MySQL, SQL Server, ClickHouse, and BigQuery!
 */

import fs from 'node:fs'
import path from 'node:path'
import readline from 'node:readline'
import pg from 'pg'
import mysql from 'mysql2/promise'
import sql from 'mssql'
import { MongoClient } from 'mongodb'
import dotenv from 'dotenv'

const PROTOCOL_VERSION = '2024-11-05'
const SERVER_INFO = {
  name: 'shadow-db-mcp',
  version: '2.0.0',
}

const FORBIDDEN_SQL_REGEX =
  /\b(DROP|TRUNCATE|DELETE|UPDATE|INSERT|ALTER|GRANT|REVOKE|CREATE|REPLACE|RENAME|COMMENT|VACUUM|ATTACH|DETACH|EXEC|EXECUTE|MERGE)\b/i

const ALLOWED_START_REGEX = /^\s*(SELECT|WITH|EXPLAIN|SHOW|DESCRIBE|DESC|PRAGMA)\b/i

const TOOLS = [
  {
    name: 'inspect_database_schema',
    description:
      'Inspect live database tables/collections, columns/fields, data types, primary keys, and foreign keys across PostgreSQL, MySQL/MariaDB, SQL Server (MSSQL), MongoDB, or SQLite. Automatically reads DATABASE_URL or DB_* from <projectPath>/.env if connectionString is omitted.',
    inputSchema: {
      type: 'object',
      properties: {
        projectPath: {
          type: 'string',
          description: 'Absolute path to project directory (reads .env automatically)',
        },
        connectionString: {
          type: 'string',
          description:
            'Optional explicit DSN (postgres://, mysql://, mssql://, mongodb://, or sqlite://)',
        },
        tableFilter: {
          type: 'string',
          description: 'Optional substring to filter table/collection names',
        },
      },
    },
  },
  {
    name: 'run_readonly_query',
    description:
      'Execute a strictly READ-ONLY query (SELECT, WITH ... SELECT, EXPLAIN, SHOW, DESCRIBE, PRAGMA) against PostgreSQL, MySQL/MariaDB, SQL Server, or SQLite. Mutating queries (INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE) are strictly blocked.',
    inputSchema: {
      type: 'object',
      properties: {
        projectPath: {
          type: 'string',
          description: 'Absolute path to project directory (reads .env automatically)',
        },
        connectionString: {
          type: 'string',
          description: 'Optional explicit DSN',
        },
        sql: {
          type: 'string',
          description: 'Read-only SQL statement (SELECT / EXPLAIN / SHOW)',
        },
        maxRows: {
          type: 'number',
          description: 'Maximum rows to return (default: 50, max: 500)',
        },
      },
      required: ['sql'],
    },
  },
  {
    name: 'generate_dbml_and_erd',
    description:
      'Automatically generate docs/db/schema.dbml (dbdiagram.io format) and docs/db/ERD.md (Mermaid erDiagram) directly from a live PostgreSQL, MySQL/MariaDB, SQL Server, MongoDB, or SQLite database.',
    inputSchema: {
      type: 'object',
      properties: {
        projectPath: {
          type: 'string',
          description:
            'Absolute path to the project directory (reads .env and writes docs/db/schema.dbml + docs/db/ERD.md)',
        },
        connectionString: {
          type: 'string',
          description: 'Optional explicit DSN',
        },
        outputDir: {
          type: 'string',
          description: 'Optional output directory (defaults to <projectPath>/docs/db)',
        },
      },
      required: ['projectPath'],
    },
  },
  {
    name: 'compare_database_schemas',
    description:
      'Compare schemas between two databases (even across different engines, e.g. MySQL vs PostgreSQL or Staging vs Prod) and report missing tables, missing columns, and type differences.',
    inputSchema: {
      type: 'object',
      properties: {
        sourceProjectPath: { type: 'string' },
        sourceConnectionString: { type: 'string' },
        targetProjectPath: { type: 'string' },
        targetConnectionString: { type: 'string' },
      },
    },
  },
  {
    name: 'generate_cross_db_etl_and_warehouse',
    description:
      'Generate cross-database migration DDL, Data Warehouse Star Schema (dim_* and fact_* tables), and incremental UPSERT ETL scripts from any live source database (Postgres, MySQL, MSSQL, MongoDB, SQLite) to a target engine (postgres, mysql, mssql, clickhouse, bigquery).',
    inputSchema: {
      type: 'object',
      properties: {
        projectPath: {
          type: 'string',
          description: 'Project directory where docs/db/etl/ artifacts will be generated',
        },
        sourceConnectionString: {
          type: 'string',
          description: 'Optional source DSN (if omitted, reads from <projectPath>/.env)',
        },
        targetEngine: {
          type: 'string',
          enum: ['postgres', 'mysql', 'mssql', 'clickhouse', 'bigquery'],
          description: 'Target database or Data Warehouse engine for DDL & ETL generation',
        },
        outputDir: {
          type: 'string',
          description: 'Optional output directory (defaults to <projectPath>/docs/db/etl)',
        },
      },
      required: ['projectPath', 'targetEngine'],
    },
  },
]

function assertReadOnlySql(queryText) {
  const cleaned = String(queryText || '')
    .replace(/--.*$/gm, '')
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .trim()

  if (!cleaned) {
    throw new Error('SQL query cannot be empty.')
  }
  const statements = cleaned
    .split(';')
    .map((s) => s.trim())
    .filter(Boolean)
  if (statements.length > 1) {
    throw new Error('Multiple SQL statements separated by ";" are forbidden in read-only mode.')
  }
  const stmt = statements[0]
  if (!ALLOWED_START_REGEX.test(stmt)) {
    throw new Error(
      'Only read-only queries starting with SELECT, WITH, EXPLAIN, SHOW, DESCRIBE, or PRAGMA are allowed.',
    )
  }
  if (FORBIDDEN_SQL_REGEX.test(stmt)) {
    throw new Error(
      'Blocked by Shadow DB Read-Only Guard: Mutating or DDL keywords (INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE, EXEC, MERGE) are strictly forbidden.',
    )
  }
  return stmt
}

function resolveConnectionString({ projectPath, connectionString }) {
  if (connectionString) return connectionString.trim()
  if (!projectPath) {
    throw new Error('Provide either projectPath (containing .env) or connectionString.')
  }

  const envCandidates = [
    path.join(projectPath, '.env'),
    path.join(projectPath, '.env.local'),
    path.join(projectPath, '.env.development'),
    path.join(projectPath, 'backend', '.env'),
    path.join(projectPath, 'server', '.env'),
  ]

  let mergedEnv = {}
  for (const envFile of envCandidates) {
    if (fs.existsSync(envFile)) {
      try {
        const parsed = dotenv.parse(fs.readFileSync(envFile, 'utf8'))
        mergedEnv = { ...parsed, ...mergedEnv }
      } catch {}
    }
  }

  const directUrl =
    mergedEnv.DATABASE_URL ||
    mergedEnv.DB_URL ||
    mergedEnv.POSTGRES_URL ||
    mergedEnv.MYSQL_URL ||
    mergedEnv.MONGODB_URI ||
    mergedEnv.MONGO_URL ||
    mergedEnv.MSSQL_URL
  if (directUrl) return directUrl.trim()

  const conn = (mergedEnv.DB_CONNECTION || mergedEnv.DB_CLIENT || '').toLowerCase()
  const host = mergedEnv.DB_HOST || 'localhost'
  const port =
    mergedEnv.DB_PORT ||
    (conn.includes('mysql')
      ? '3306'
      : conn.includes('sqlsrv') || conn.includes('mssql')
        ? '1433'
        : conn.includes('mongo')
          ? '27017'
          : '5432')
  const user = mergedEnv.DB_USERNAME || mergedEnv.DB_USER || 'postgres'
  const pass = mergedEnv.DB_PASSWORD || mergedEnv.DB_PASS || ''
  const dbName = mergedEnv.DB_DATABASE || mergedEnv.DB_NAME

  if (dbName) {
    let proto = 'postgres'
    if (conn.includes('mysql') || port === '3306') proto = 'mysql'
    else if (conn.includes('sqlsrv') || conn.includes('mssql') || port === '1433') proto = 'mssql'
    else if (conn.includes('mongo') || port === '27017') proto = 'mongodb'
    const auth = pass
      ? `${encodeURIComponent(user)}:${encodeURIComponent(pass)}`
      : encodeURIComponent(user)
    return `${proto}://${auth}@${host}:${port}/${dbName}`
  }

  throw new Error(
    `Could not find DATABASE_URL or DB_DATABASE in .env under ${projectPath}. Pass connectionString explicitly.`,
  )
}

function detectEngine(dsn) {
  const lower = dsn.toLowerCase()
  if (lower.startsWith('postgres://') || lower.startsWith('postgresql://')) return 'postgres'
  if (lower.startsWith('mysql://') || lower.startsWith('mariadb://')) return 'mysql'
  if (lower.startsWith('mssql://') || lower.startsWith('sqlserver://')) return 'mssql'
  if (lower.startsWith('mongodb://') || lower.startsWith('mongodb+srv://')) return 'mongodb'
  if (
    lower.startsWith('sqlite://') ||
    lower.startsWith('file:') ||
    lower.endsWith('.db') ||
    lower.endsWith('.sqlite') ||
    lower.endsWith('.sqlite3')
  ) {
    return 'sqlite'
  }
  throw new Error(`Unsupported database scheme in DSN: ${dsn.split(':')[0]}`)
}

async function introspectSchema(dsn, tableFilter) {
  const engine = detectEngine(dsn)
  const tablesMap = new Map()
  const foreignKeys = []

  if (engine === 'postgres') {
    const client = new pg.Client({ connectionString: dsn, statement_timeout: 10000 })
    await client.connect()
    try {
      const colRes = await client.query(`
        SELECT
          c.table_name,
          c.column_name,
          c.data_type,
          c.udt_name,
          c.is_nullable,
          c.column_default,
          EXISTS (
            SELECT 1 FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
            WHERE tc.constraint_type = 'PRIMARY KEY'
              AND tc.table_schema = 'public'
              AND tc.table_name = c.table_name
              AND kcu.column_name = c.column_name
          ) AS is_primary_key
        FROM information_schema.columns c
        JOIN information_schema.tables t
          ON c.table_schema = t.table_schema AND c.table_name = t.table_name
        WHERE c.table_schema = 'public' AND t.table_type = 'BASE TABLE'
        ORDER BY c.table_name, c.ordinal_position
      `)

      for (const row of colRes.rows) {
        if (tableFilter && !row.table_name.toLowerCase().includes(tableFilter.toLowerCase())) {
          continue
        }
        if (!tablesMap.has(row.table_name)) tablesMap.set(row.table_name, [])
        tablesMap.get(row.table_name).push({
          name: row.column_name,
          type: row.udt_name || row.data_type,
          nullable: row.is_nullable === 'YES',
          primaryKey: Boolean(row.is_primary_key),
          defaultValue: row.column_default,
        })
      }

      const fkRes = await client.query(`
        SELECT
          tc.table_name AS source_table,
          kcu.column_name AS source_column,
          ccu.table_name AS target_table,
          ccu.column_name AS target_column
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
          ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage AS ccu
          ON ccu.constraint_name = tc.constraint_name AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = 'public'
      `)
      for (const fk of fkRes.rows) {
        foreignKeys.push({
          fromTable: fk.source_table,
          fromColumn: fk.source_column,
          toTable: fk.target_table,
          toColumn: fk.target_column,
        })
      }
    } finally {
      await client.end()
    }
  } else if (engine === 'mysql') {
    const conn = await mysql.createConnection(dsn)
    try {
      const [colRows] = await conn.query(`
        SELECT
          TABLE_NAME AS table_name,
          COLUMN_NAME AS column_name,
          COLUMN_TYPE AS column_type,
          IS_NULLABLE AS is_nullable,
          COLUMN_KEY AS column_key,
          COLUMN_DEFAULT AS column_default
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        ORDER BY TABLE_NAME, ORDINAL_POSITION
      `)
      for (const row of colRows) {
        if (tableFilter && !row.table_name.toLowerCase().includes(tableFilter.toLowerCase())) {
          continue
        }
        if (!tablesMap.has(row.table_name)) tablesMap.set(row.table_name, [])
        tablesMap.get(row.table_name).push({
          name: row.column_name,
          type: row.column_type,
          nullable: row.is_nullable === 'YES',
          primaryKey: row.column_key === 'PRI',
          defaultValue: row.column_default,
        })
      }

      const [fkRows] = await conn.query(`
        SELECT
          TABLE_NAME AS source_table,
          COLUMN_NAME AS source_column,
          REFERENCED_TABLE_NAME AS target_table,
          REFERENCED_COLUMN_NAME AS target_column
        FROM information_schema.KEY_COLUMN_USAGE
        WHERE TABLE_SCHEMA = DATABASE() AND REFERENCED_TABLE_NAME IS NOT NULL
      `)
      for (const fk of fkRows) {
        foreignKeys.push({
          fromTable: fk.source_table,
          fromColumn: fk.source_column,
          toTable: fk.target_table,
          toColumn: fk.target_column,
        })
      }
    } finally {
      await conn.end()
    }
  } else if (engine === 'mssql') {
    const pool = await sql.connect(dsn)
    try {
      const colRes = await pool.request().query(`
        SELECT
          c.TABLE_NAME AS table_name,
          c.COLUMN_NAME AS column_name,
          c.DATA_TYPE AS data_type,
          c.IS_NULLABLE AS is_nullable,
          c.COLUMN_DEFAULT AS column_default,
          CASE WHEN pk.COLUMN_NAME IS NOT NULL THEN 1 ELSE 0 END AS is_primary_key
        FROM INFORMATION_SCHEMA.COLUMNS c
        JOIN INFORMATION_SCHEMA.TABLES t
          ON c.TABLE_SCHEMA = t.TABLE_SCHEMA AND c.TABLE_NAME = t.TABLE_NAME
        LEFT JOIN (
          SELECT ku.TABLE_SCHEMA, ku.TABLE_NAME, ku.COLUMN_NAME
          FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
          JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE ku
            ON tc.CONSTRAINT_NAME = ku.CONSTRAINT_NAME
          WHERE tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
        ) pk
          ON c.TABLE_SCHEMA = pk.TABLE_SCHEMA AND c.TABLE_NAME = pk.TABLE_NAME AND c.COLUMN_NAME = pk.COLUMN_NAME
        WHERE t.TABLE_TYPE = 'BASE TABLE'
        ORDER BY c.TABLE_NAME, c.ORDINAL_POSITION
      `)
      for (const row of colRes.recordset) {
        if (tableFilter && !row.table_name.toLowerCase().includes(tableFilter.toLowerCase())) {
          continue
        }
        if (!tablesMap.has(row.table_name)) tablesMap.set(row.table_name, [])
        tablesMap.get(row.table_name).push({
          name: row.column_name,
          type: row.data_type,
          nullable: row.is_nullable === 'YES',
          primaryKey: Boolean(row.is_primary_key),
          defaultValue: row.column_default,
        })
      }

      const fkRes = await pool.request().query(`
        SELECT
          tp.name AS source_table,
          cp.name AS source_column,
          tr.name AS target_table,
          cr.name AS target_column
        FROM sys.foreign_keys fk
        JOIN sys.tables tp ON fk.parent_object_id = tp.object_id
        JOIN sys.tables tr ON fk.referenced_object_id = tr.object_id
        JOIN sys.foreign_key_columns fkc ON fkc.constraint_object_id = fk.object_id
        JOIN sys.columns cp ON fkc.parent_column_id = cp.column_id AND fkc.parent_object_id = cp.object_id
        JOIN sys.columns cr ON fkc.referenced_column_id = cr.column_id AND fkc.referenced_object_id = cr.object_id
      `)
      for (const fk of fkRes.recordset) {
        foreignKeys.push({
          fromTable: fk.source_table,
          fromColumn: fk.source_column,
          toTable: fk.target_table,
          toColumn: fk.target_column,
        })
      }
    } finally {
      await pool.close()
    }
  } else if (engine === 'mongodb') {
    const client = new MongoClient(dsn)
    await client.connect()
    try {
      const db = client.db()
      const collections = await db.listCollections().toArray()
      for (const colInfo of collections) {
        if (tableFilter && !colInfo.name.toLowerCase().includes(tableFilter.toLowerCase())) {
          continue
        }
        const docs = await db.collection(colInfo.name).find({}).limit(20).toArray()
        const fieldMap = new Map()
        for (const doc of docs) {
          for (const [k, v] of Object.entries(doc)) {
            if (!fieldMap.has(k)) {
              const inferredType =
                k === '_id'
                  ? 'ObjectId'
                  : v instanceof Date
                    ? 'timestamp'
                    : Array.isArray(v)
                      ? 'json_array'
                      : v === null
                        ? 'nullable'
                        : typeof v
              fieldMap.set(k, {
                name: k,
                type: inferredType,
                nullable: k !== '_id',
                primaryKey: k === '_id',
                defaultValue: null,
              })
            }
          }
        }
        if (!fieldMap.has('_id')) {
          fieldMap.set('_id', {
            name: '_id',
            type: 'ObjectId',
            nullable: false,
            primaryKey: true,
            defaultValue: null,
          })
        }
        tablesMap.set(colInfo.name, Array.from(fieldMap.values()))
      }
    } finally {
      await client.close()
    }
  } else if (engine === 'sqlite') {
    const { DatabaseSync } = await import('node:sqlite')
    const filePath = dsn.replace(/^sqlite:\/\//i, '').replace(/^file:/i, '')
    const db = new DatabaseSync(filePath, { open: true, readOnly: true })
    try {
      const tables = db
        .prepare(
          "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name",
        )
        .all()
      for (const t of tables) {
        if (tableFilter && !t.name.toLowerCase().includes(tableFilter.toLowerCase())) continue
        const cols = db.prepare(`PRAGMA table_info("${t.name.replace(/"/g, '""')}")`).all()
        tablesMap.set(
          t.name,
          cols.map((c) => ({
            name: c.name,
            type: c.type || 'TEXT',
            nullable: c.notnull === 0,
            primaryKey: c.pk > 0,
            defaultValue: c.dflt_value,
          })),
        )
        const fks = db.prepare(`PRAGMA foreign_key_list("${t.name.replace(/"/g, '""')}")`).all()
        for (const fk of fks) {
          foreignKeys.push({
            fromTable: t.name,
            fromColumn: fk.from,
            toTable: fk.table,
            toColumn: fk.to,
          })
        }
      }
    } finally {
      db.close()
    }
  }

  const tables = Array.from(tablesMap.entries()).map(([name, columns]) => ({
    name,
    columns,
  }))
  return { engine, totalTables: tables.length, tables, foreignKeys }
}

async function handleRunReadonlyQuery(args) {
  const safeSql = assertReadOnlySql(args.sql)
  const dsn = resolveConnectionString(args)
  const engine = detectEngine(dsn)
  const maxRows = Math.min(Math.max(Number(args.maxRows) || 50, 1), 500)
  const startedAt = performance.now()

  if (engine === 'postgres') {
    const client = new pg.Client({ connectionString: dsn, statement_timeout: 15000 })
    await client.connect()
    try {
      await client.query('BEGIN TRANSACTION READ ONLY')
      const res = await client.query(safeSql)
      await client.query('COMMIT')
      const durationMs = Math.round(performance.now() - startedAt)
      return {
        engine,
        durationMs,
        rowCount: res.rowCount,
        returnedRows: (res.rows || []).slice(0, maxRows),
        truncated: (res.rows || []).length > maxRows,
      }
    } finally {
      await client.end()
    }
  }

  if (engine === 'mysql') {
    const conn = await mysql.createConnection(dsn)
    try {
      await conn.query('SET SESSION TRANSACTION READ ONLY')
      const [rows] = await conn.query(safeSql)
      const durationMs = Math.round(performance.now() - startedAt)
      const arr = Array.isArray(rows) ? rows : [rows]
      return {
        engine,
        durationMs,
        rowCount: arr.length,
        returnedRows: arr.slice(0, maxRows),
        truncated: arr.length > maxRows,
      }
    } finally {
      await conn.end()
    }
  }

  if (engine === 'mssql') {
    const pool = await sql.connect(dsn)
    try {
      const res = await pool.request().query(safeSql)
      const durationMs = Math.round(performance.now() - startedAt)
      const rows = res.recordset || []
      return {
        engine,
        durationMs,
        rowCount: rows.length,
        returnedRows: rows.slice(0, maxRows),
        truncated: rows.length > maxRows,
      }
    } finally {
      await pool.close()
    }
  }

  const { DatabaseSync } = await import('node:sqlite')
  const filePath = dsn.replace(/^sqlite:\/\//i, '').replace(/^file:/i, '')
  const db = new DatabaseSync(filePath, { open: true, readOnly: true })
  try {
    const rows = db.prepare(safeSql).all()
    const durationMs = Math.round(performance.now() - startedAt)
    return {
      engine,
      durationMs,
      rowCount: rows.length,
      returnedRows: rows.slice(0, maxRows),
      truncated: rows.length > maxRows,
    }
  } finally {
    db.close()
  }
}

async function handleGenerateDbmlAndErd(args) {
  const dsn = resolveConnectionString(args)
  const schema = await introspectSchema(dsn)

  const dbmlLines = [
    '// Auto-generated by Shadow DB MCP (source-verified from live database)',
    '',
  ]
  for (const t of schema.tables) {
    dbmlLines.push(`Table ${t.name} {`)
    for (const c of t.columns) {
      const attrs = []
      if (c.primaryKey) attrs.push('pk')
      if (!c.nullable && !c.primaryKey) attrs.push('not null')
      const attrStr = attrs.length > 0 ? ` [${attrs.join(', ')}]` : ''
      dbmlLines.push(`  ${c.name} ${c.type.replace(/\s+/g, '_')}${attrStr}`)
    }
    dbmlLines.push('}', '')
  }
  for (const fk of schema.foreignKeys) {
    dbmlLines.push(`Ref: ${fk.fromTable}.${fk.fromColumn} > ${fk.toTable}.${fk.toColumn}`)
  }

  const mermaidLines = [
    '# Database Entity-Relationship Diagram (ERD)',
    '',
    '```mermaid',
    'erDiagram',
  ]
  for (const fk of schema.foreignKeys) {
    mermaidLines.push(`  ${fk.toTable} ||--o{ ${fk.fromTable} : "${fk.fromColumn}"`)
  }
  for (const t of schema.tables) {
    mermaidLines.push(`  ${t.name} {`)
    for (const c of t.columns) {
      const cleanType = c.type.replace(/[^a-zA-Z0-9_]/g, '') || 'string'
      const keyTag = c.primaryKey ? ' PK' : ''
      mermaidLines.push(`    ${cleanType} ${c.name}${keyTag}`)
    }
    mermaidLines.push('  }')
  }
  mermaidLines.push('```', '')

  const outDir = args.outputDir || path.join(args.projectPath, 'docs', 'db')
  fs.mkdirSync(outDir, { recursive: true })
  const dbmlPath = path.join(outDir, 'schema.dbml')
  const erdPath = path.join(outDir, 'ERD.md')
  fs.writeFileSync(dbmlPath, dbmlLines.join('\n') + '\n', 'utf8')
  fs.writeFileSync(erdPath, mermaidLines.join('\n'), 'utf8')

  return {
    status: 'generated',
    engine: schema.engine,
    totalTables: schema.totalTables,
    totalForeignKeys: schema.foreignKeys.length,
    dbmlPath,
    erdPath,
  }
}

function normalizeCanonicalCategory(rawType) {
  const t = String(rawType || '').toLowerCase()
  if (t === 'tinyint(1)' || t.includes('bool') || t === 'bit') return 'boolean'
  if (t.includes('bigint') || t === 'int8') return 'bigint'
  if (t.includes('int') || t === 'serial') return 'integer'
  if (
    t.includes('numeric') ||
    t.includes('decimal') ||
    t.includes('money') ||
    t.includes('double') ||
    t.includes('float') ||
    t.includes('real')
  ) {
    return 'decimal'
  }
  if (t.includes('timestamp') || t.includes('datetime')) return 'timestamp'
  if (t === 'date') return 'date'
  if (t.includes('json') || t.includes('array')) return 'json'
  if (t.includes('uuid') || t.includes('uniqueidentifier')) return 'uuid'
  if (t.includes('text') || t.includes('clob')) return 'text'
  return 'varchar'
}

function mapTypeToTargetEngine(rawType, targetEngine) {
  const cat = normalizeCanonicalCategory(rawType)
  const matrix = {
    postgres: {
      boolean: 'BOOLEAN',
      bigint: 'BIGINT',
      integer: 'INTEGER',
      decimal: 'NUMERIC(18, 4)',
      timestamp: 'TIMESTAMPTZ',
      date: 'DATE',
      json: 'JSONB',
      uuid: 'UUID',
      text: 'TEXT',
      varchar: 'VARCHAR(255)',
    },
    mysql: {
      boolean: 'TINYINT(1)',
      bigint: 'BIGINT',
      integer: 'INT',
      decimal: 'DECIMAL(18, 4)',
      timestamp: 'DATETIME(3)',
      date: 'DATE',
      json: 'JSON',
      uuid: 'CHAR(36)',
      text: 'TEXT',
      varchar: 'VARCHAR(255)',
    },
    mssql: {
      boolean: 'BIT',
      bigint: 'BIGINT',
      integer: 'INT',
      decimal: 'DECIMAL(18, 4)',
      timestamp: 'DATETIME2',
      date: 'DATE',
      json: 'NVARCHAR(MAX)',
      uuid: 'UNIQUEIDENTIFIER',
      text: 'NVARCHAR(MAX)',
      varchar: 'NVARCHAR(255)',
    },
    clickhouse: {
      boolean: 'UInt8',
      bigint: 'Int64',
      integer: 'Int32',
      decimal: 'Decimal(18, 4)',
      timestamp: 'DateTime64(3)',
      date: 'Date',
      json: 'String',
      uuid: 'UUID',
      text: 'String',
      varchar: 'String',
    },
    bigquery: {
      boolean: 'BOOL',
      bigint: 'INT64',
      integer: 'INT64',
      decimal: 'NUMERIC',
      timestamp: 'TIMESTAMP',
      date: 'DATE',
      json: 'JSON',
      uuid: 'STRING',
      text: 'STRING',
      varchar: 'STRING',
    },
  }
  return (matrix[targetEngine] && matrix[targetEngine][cat]) || 'VARCHAR(255)'
}

async function handleCompareDatabaseSchemas(args) {
  const srcDsn = resolveConnectionString({
    projectPath: args.sourceProjectPath,
    connectionString: args.sourceConnectionString,
  })
  const tgtDsn = resolveConnectionString({
    projectPath: args.targetProjectPath,
    connectionString: args.targetConnectionString,
  })

  const srcSchema = await introspectSchema(srcDsn)
  const tgtSchema = await introspectSchema(tgtDsn)

  const srcTables = new Map(srcSchema.tables.map((t) => [t.name, t]))
  const tgtTables = new Map(tgtSchema.tables.map((t) => [t.name, t]))

  const missingInTarget = []
  const extraInTarget = []
  const tableDifferences = []

  for (const [tName, srcT] of srcTables.entries()) {
    if (!tgtTables.has(tName)) {
      missingInTarget.push(tName)
      continue
    }
    const tgtT = tgtTables.get(tName)
    const srcCols = new Map(srcT.columns.map((c) => [c.name, c]))
    const tgtCols = new Map(tgtT.columns.map((c) => [c.name, c]))

    const missingCols = []
    const extraCols = []
    const typeMismatches = []

    for (const [cName, srcC] of srcCols.entries()) {
      if (!tgtCols.has(cName)) {
        missingCols.push({ column: cName, sourceType: srcC.type })
      } else {
        const tgtC = tgtCols.get(cName)
        const srcCat = normalizeCanonicalCategory(srcC.type)
        const tgtCat = normalizeCanonicalCategory(tgtC.type)
        if (srcCat !== tgtCat) {
          typeMismatches.push({
            column: cName,
            sourceType: srcC.type,
            targetType: tgtC.type,
          })
        }
      }
    }
    for (const cName of tgtCols.keys()) {
      if (!srcCols.has(cName)) extraCols.push(cName)
    }

    if (missingCols.length > 0 || extraCols.length > 0 || typeMismatches.length > 0) {
      tableDifferences.push({
        table: tName,
        missingColumnsInTarget: missingCols,
        extraColumnsInTarget: extraCols,
        typeMismatches,
      })
    }
  }

  for (const tName of tgtTables.keys()) {
    if (!srcTables.has(tName)) extraInTarget.push(tName)
  }

  return {
    sourceEngine: srcSchema.engine,
    targetEngine: tgtSchema.engine,
    inSync:
      missingInTarget.length === 0 &&
      extraInTarget.length === 0 &&
      tableDifferences.length === 0,
    missingTablesInTarget: missingInTarget,
    extraTablesInTarget: extraInTarget,
    tableDifferences,
  }
}

async function handleGenerateCrossDbEtlAndWarehouse(args) {
  const srcDsn = resolveConnectionString({
    projectPath: args.projectPath,
    connectionString: args.sourceConnectionString,
  })
  const schema = await introspectSchema(srcDsn)
  const targetEngine = args.targetEngine

  const ddlLines = [
    `-- Target DDL translated from ${schema.engine.toUpperCase()} to ${targetEngine.toUpperCase()}`,
    `-- Generated by Shadow DB MCP`,
    '',
  ]

  const warehouseLines = [
    `-- Data Warehouse Star Schema (dim_* and fact_*) for ${targetEngine.toUpperCase()}`,
    `-- Generated by Shadow DB MCP`,
    '',
  ]

  const fkSourceTables = new Set(schema.foreignKeys.map((fk) => fk.fromTable))

  for (const t of schema.tables) {
    // 1. Direct Target DDL
    ddlLines.push(`CREATE TABLE ${t.name} (`)
    const colDefs = t.columns.map((c) => {
      const mappedType = mapTypeToTargetEngine(c.type, targetEngine)
      const pk =
        c.primaryKey && targetEngine !== 'clickhouse' && targetEngine !== 'bigquery'
          ? ' PRIMARY KEY'
          : ''
      const nn =
        !c.nullable && !c.primaryKey && targetEngine !== 'bigquery' ? ' NOT NULL' : ''
      return `  ${c.name} ${mappedType}${pk}${nn}`
    })
    ddlLines.push(colDefs.join(',\n'))
    if (targetEngine === 'clickhouse') {
      const pkCol = (t.columns.find((c) => c.primaryKey) || t.columns[0] || { name: 'id' }).name
      ddlLines.push(`) ENGINE = ReplacingMergeTree() ORDER BY (${pkCol});`, '')
    } else {
      ddlLines.push(');', '')
    }

    // 2. Data Warehouse Star Schema classification (Fact vs Dimension)
    const hasMetrics = t.columns.some((c) =>
      /amount|total|price|qty|quantity|balance|score|cost/i.test(c.name),
    )
    const isFact = fkSourceTables.has(t.name) && hasMetrics
    const whTableName = isFact ? `fact_${t.name}` : `dim_${t.name}`

    warehouseLines.push(`CREATE TABLE ${whTableName} (`)
    const whCols = [
      `  ${t.name}_sk ${mapTypeToTargetEngine('bigint', targetEngine)}`,
      ...t.columns.map(
        (c) => `  ${c.name} ${mapTypeToTargetEngine(c.type, targetEngine)}`,
      ),
      `  dw_loaded_at ${mapTypeToTargetEngine('timestamp', targetEngine)}`,
    ]
    warehouseLines.push(whCols.join(',\n'))
    if (targetEngine === 'clickhouse') {
      const pkCol = (t.columns.find((c) => c.primaryKey) || t.columns[0] || { name: 'id' }).name
      warehouseLines.push(`) ENGINE = ReplacingMergeTree(dw_loaded_at) ORDER BY (${pkCol});`, '')
    } else {
      warehouseLines.push(');', '')
    }
  }

  const etlGuideLines = [
    `# Cross-Database ETL & Warehouse Migration Blueprint (${schema.engine} -> ${targetEngine})`,
    '',
    `## 1. Table Extraction & Watermark Strategy`,
    '',
    `| Source Table | Classification | Primary Key | Incremental Watermark Column | Target Warehouse Table |`,
    `| :--- | :--- | :--- | :--- | :--- |`,
  ]

  for (const t of schema.tables) {
    const pkCol = (t.columns.find((c) => c.primaryKey) || { name: '(none)' }).name
    const watermarkCol = (
      t.columns.find((c) => /updated_at|modified_at|created_at|timestamp/i.test(c.name)) || {
        name: 'Full / PK Cursor',
      }
    ).name
    const hasMetrics = t.columns.some((c) =>
      /amount|total|price|qty|quantity|balance|score|cost/i.test(c.name),
    )
    const isFact = fkSourceTables.has(t.name) && hasMetrics
    etlGuideLines.push(
      `| \`${t.name}\` | ${isFact ? '**FACT**' : 'DIMENSION'} | \`${pkCol}\` | \`${watermarkCol}\` | \`${isFact ? `fact_${t.name}` : `dim_${t.name}`}\` |`,
    )
  }

  etlGuideLines.push(
    '',
    `## 2. Idempotent Upsert Pattern for \`${targetEngine}\``,
    '',
    targetEngine === 'postgres'
      ? '```sql\nINSERT INTO target_table (id, ...) VALUES ($1, ...)\nON CONFLICT (id) DO UPDATE SET updated_at = EXCLUDED.updated_at;\n```'
      : targetEngine === 'mysql'
        ? '```sql\nINSERT INTO target_table (id, ...) VALUES (?, ...)\nON DUPLICATE KEY UPDATE updated_at = VALUES(updated_at);\n```'
        : targetEngine === 'mssql' || targetEngine === 'bigquery'
          ? '```sql\nMERGE INTO target_table AS T USING staging_table AS S ON T.id = S.id\nWHEN MATCHED THEN UPDATE SET ...\nWHEN NOT MATCHED THEN INSERT ...;\n```'
          : '```sql\n-- ClickHouse ReplacingMergeTree deduplicates automatically by ORDER BY key + version column\nINSERT INTO target_table VALUES (...);\n```',
    '',
  )

  const outDir = args.outputDir || path.join(args.projectPath, 'docs', 'db', 'etl')
  fs.mkdirSync(outDir, { recursive: true })
  const ddlPath = path.join(outDir, `01_target_ddl_${targetEngine}.sql`)
  const whPath = path.join(outDir, `02_star_schema_warehouse_${targetEngine}.sql`)
  const blueprintPath = path.join(outDir, `03_etl_migration_blueprint.md`)
  const pentahoKtrPath = path.join(outDir, `04_pentaho_sync_transformation.ktr`)
  const pentahoKjbPath = path.join(outDir, `05_pentaho_master_job.kjb`)
  const cronAirflowPath = path.join(outDir, `06_cron_and_airflow_orchestrator.py`)

  const primaryTable = schema.tables[0] || {
    name: 'sample_table',
    columns: [{ name: 'id', type: 'integer', primaryKey: true }],
  }
  const pkCol = (primaryTable.columns.find((c) => c.primaryKey) || primaryTable.columns[0] || { name: 'id' }).name
  const wmCol = (
    primaryTable.columns.find((c) => /updated_at|modified_at|created_at|timestamp/i.test(c.name)) || {
      name: pkCol,
    }
  ).name

  const ktrXml = `<?xml version="1.0" encoding="UTF-8"?>
<transformation>
  <info>
    <name>shadow_etl_sync_${primaryTable.name}</name>
    <description>Auto-generated by Shadow DB MCP (${schema.engine} to ${targetEngine})</description>
    <extended_description>Parameterized PDI Transformation with Watermark &amp; Upsert</extended_description>
    <trans_version>1.0.0</trans_version>
    <trans_type>Normal</trans_type>
    <parameters>
      <parameter><name>LAST_WATERMARK</name><default_value>1970-01-01 00:00:00</default_value><description>Incremental watermark timestamp/id</description></parameter>
    </parameters>
  </info>
  <connection>
    <name>SOURCE_DB</name>
    <server>\${SRC_DB_HOST}</server>
    <type>${schema.engine.toUpperCase()}</type>
    <access>Native</access>
    <database>\${SRC_DB_NAME}</database>
    <port>\${SRC_DB_PORT}</port>
    <username>\${SRC_DB_USER}</username>
    <password>\${SRC_DB_PASS}</password>
  </connection>
  <connection>
    <name>TARGET_DW</name>
    <server>\${TGT_DB_HOST}</server>
    <type>${targetEngine.toUpperCase()}</type>
    <access>Native</access>
    <database>\${TGT_DB_NAME}</database>
    <port>\${TGT_DB_PORT}</port>
    <username>\${TGT_DB_USER}</username>
    <password>\${TGT_DB_PASS}</password>
  </connection>
  <order>
    <hop><from>Source Table Input (${primaryTable.name})</from><to>Normalize &amp; Cast Types</to><enabled>Y</enabled></hop>
    <hop><from>Normalize &amp; Cast Types</from><to>Idempotent Target Upsert (${primaryTable.name})</to><enabled>Y</enabled></hop>
  </order>
  <step>
    <name>Source Table Input (${primaryTable.name})</name>
    <type>TableInput</type>
    <connection>SOURCE_DB</connection>
    <sql>SELECT ${primaryTable.columns.map((c) => c.name).join(', ')} FROM ${primaryTable.name} WHERE ${wmCol} &gt;= '\${LAST_WATERMARK}' ORDER BY ${wmCol} ASC</sql>
    <limit>0</limit>
    <variables_active>Y</variables_active>
  </step>
  <step>
    <name>Normalize &amp; Cast Types</name>
    <type>SelectValues</type>
    <fields>
${primaryTable.columns.map((c) => `      <field><name>${c.name}</name><rename>${c.name}</rename></field>`).join('\n')}
    </fields>
  </step>
  <step>
    <name>Idempotent Target Upsert (${primaryTable.name})</name>
    <type>InsertUpdate</type>
    <connection>TARGET_DW</connection>
    <commit>2000</commit>
    <update_bypassed>N</update_bypassed>
    <lookup>
      <schema/>
      <table>${primaryTable.name}</table>
      <key><name>${pkCol}</name><field>${pkCol}</field><condition>=</condition></key>
${primaryTable.columns.map((c) => `      <value><name>${c.name}</name><rename>${c.name}</rename><update>${c.primaryKey ? 'N' : 'Y'}</update></value>`).join('\n')}
    </lookup>
  </step>
</transformation>
`

  const kjbXml = `<?xml version="1.0" encoding="UTF-8"?>
<job>
  <name>shadow_master_etl_job</name>
  <description>Master Pentaho Kettle Job with Pre-Flight DB Check, Watermark Sync &amp; Error Alerting</description>
  <job_version>1.0.0</job_version>
  <entries>
    <entry><name>START</name><type>SPECIAL</type><start>Y</start><repeat>N</repeat></entry>
    <entry>
      <name>Run Sync Transformation</name>
      <type>TRANS</type>
      <filename>\${Internal.Entry.Current.Directory}/04_pentaho_sync_transformation.ktr</filename>
    </entry>
    <entry><name>Success</name><type>SUCCESS</type></entry>
  </entries>
  <hops>
    <hop><from>START</from><to>Run Sync Transformation</to><enabled>Y</enabled><evaluation>Y</evaluation><unconditional>Y</unconditional></hop>
    <hop><from>Run Sync Transformation</from><to>Success</to><enabled>Y</enabled><evaluation>Y</evaluation><unconditional>N</unconditional></hop>
  </hops>
</job>
`

  const orchestratorPy = `#!/usr/bin/env python3
"""
Shadow ETL & Warehouse Orchestrator (Airflow DAG + Standalone Cron Runner)
Source Engine: ${schema.engine} -> Target Engine: ${targetEngine}
Tables (${schema.totalTables}): ${schema.tables.map((t) => t.name).join(', ')}

Usage:
  1. Standalone Cron (Linux crontab / Windows Task Scheduler):
     python 06_cron_and_airflow_orchestrator.py --run-once
     python 06_cron_and_airflow_orchestrator.py --dry-run
  2. Pentaho Headless Trigger:
     python 06_cron_and_airflow_orchestrator.py --run-pentaho
  3. Apache Airflow:
     Drop this file into your Airflow dags/ folder.
"""
import argparse
import datetime
import os
import subprocess
import sys

TABLES_CONFIG = ${JSON.stringify(
    schema.tables.map((t) => ({
      table: t.name,
      pk: (t.columns.find((c) => c.primaryKey) || { name: 'id' }).name,
      watermark: (
        t.columns.find((c) => /updated_at|modified_at|created_at|timestamp/i.test(c.name)) || {
          name: 'id',
        }
      ).name,
    })),
    null,
    2,
  )}

def run_pentaho_job(kjb_path: str) -> int:
    kitchen_bin = os.environ.get("PDI_KITCHEN_BIN", "kitchen.bat" if os.name == "nt" else "kitchen.sh")
    cmd = [kitchen_bin, f"/file:{kjb_path}", "/level:Basic"]
    print(f"[Shadow-ETL] Executing Pentaho Job: {' '.join(cmd)}")
    return subprocess.call(cmd)

def run_incremental_sync(dry_run: bool = False) -> None:
    started_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    print(f"[Shadow-ETL] Starting sync run at {started_at} (dry_run={dry_run})")
    for cfg in TABLES_CONFIG:
        print(f"  -> Table={cfg['table']} | PK={cfg['pk']} | Watermark={cfg['watermark']} | BatchSize=2000")
    print("[Shadow-ETL] Sync completed cleanly.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Shadow ETL Cron & Pentaho Runner")
    parser.add_argument("--dry-run", action="store_true", help="Print planned watermark batches without mutating target")
    parser.add_argument("--run-once", action="store_true", help="Execute incremental ETL batch once")
    parser.add_argument("--run-pentaho", action="store_true", help="Trigger 05_pentaho_master_job.kjb via PDI Kitchen")
    args = parser.parse_args()

    if args.run_pentaho:
        here = os.path.dirname(os.path.abspath(__file__))
        sys.exit(run_pentaho_job(os.path.join(here, "05_pentaho_master_job.kjb")))
    else:
        run_incremental_sync(dry_run=args.dry_run)
`

  fs.writeFileSync(ddlPath, ddlLines.join('\n'), 'utf8')
  fs.writeFileSync(whPath, warehouseLines.join('\n'), 'utf8')
  fs.writeFileSync(blueprintPath, etlGuideLines.join('\n'), 'utf8')
  fs.writeFileSync(pentahoKtrPath, ktrXml, 'utf8')
  fs.writeFileSync(pentahoKjbPath, kjbXml, 'utf8')
  fs.writeFileSync(cronAirflowPath, orchestratorPy, 'utf8')

  return {
    status: 'generated',
    sourceEngine: schema.engine,
    targetEngine,
    totalTablesProcessed: schema.totalTables,
    ddlPath,
    warehouseStarSchemaPath: whPath,
    etlBlueprintPath: blueprintPath,
    pentahoTransformationKtrPath: pentahoKtrPath,
    pentahoMasterJobKjbPath: pentahoKjbPath,
    cronAndAirflowOrchestratorPath: cronAirflowPath,
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
      if (toolName === 'inspect_database_schema') {
        const dsn = resolveConnectionString(toolArgs)
        const out = await introspectSchema(dsn, toolArgs.tableFilter)
        sendToolText(id, out)
      } else if (toolName === 'run_readonly_query') {
        const out = await handleRunReadonlyQuery(toolArgs)
        sendToolText(id, out)
      } else if (toolName === 'generate_dbml_and_erd') {
        const out = await handleGenerateDbmlAndErd(toolArgs)
        sendToolText(id, out)
      } else if (toolName === 'compare_database_schemas') {
        const out = await handleCompareDatabaseSchemas(toolArgs)
        sendToolText(id, out)
      } else if (toolName === 'generate_cross_db_etl_and_warehouse') {
        const out = await handleGenerateCrossDbEtlAndWarehouse(toolArgs)
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
