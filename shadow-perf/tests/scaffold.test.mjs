import assert from 'node:assert/strict'
import { test } from 'node:test'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { spawnSync } from 'node:child_process'
import { diagnose } from '../scripts/diagnose_window.mjs'

const cli = fileURLToPath(new URL('../scripts/openapi_to_k6_scaffold.mjs', import.meta.url))
const spec = {openapi:'3.1.0', servers:[{url:'https://prod.example.invalid'}], paths:{
  '/orders': {post:{requestBody:{required:true,content:{'application/json':{}}},responses:{201:{description:'Created'}}}},
  '/orders/{id}': {get:{responses:{200:{description:'OK'}}}}
}}
const journey = {steps:[
  {operation:'POST /orders', expect:201, body:{label:'fixture'}, capture:{name:'orderId',field:'id'}},
  {operation:'GET /orders/{id}', expect:200, path:{id:'$orderId'}}
], mock:[
  {method:'POST',path:'/orders',status:201,response:{id:'created/17'}},
  {method:'GET',path:'/orders/created%2F17',status:200}
]}

function setup(t, schema=spec, plan=journey) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'shadow-perf-'))
  t.after(() => fs.rmSync(dir, {recursive:true,force:true}))
  const input = path.join(dir,'api.json'), selection = path.join(dir,'journey.json')
  const output = path.join(dir,'out')
  fs.writeFileSync(input,JSON.stringify(schema)); fs.writeFileSync(selection,JSON.stringify(plan))
  const run = (...args) => spawnSync(process.execPath,[cli,'--spec',input,...args],{cwd:dir,encoding:'utf8'})
  return {dir, input, output, selection, run}
}

test('POST-only inventory stays draft; no invented traffic or production target',t => {
  const f = setup(t,{...spec,paths:{'/orders':spec.paths['/orders']}})
  const run = f.run('--out', f.output)
  assert.equal(run.status,0,run.stderr)
  const result = JSON.parse(run.stdout)
  assert.equal(result.status,'DRAFT'); assert.deepEqual(result.operations,['POST /orders'])
  for(const file of result.files) {
    const source=fs.readFileSync(file,'utf8')
    assert.doesNotMatch(source,/healthz|example\.invalid|status < 500/)
    assert.match(source,/Draft:/)
  }
})

test('mock validates create fixture, encoded captured id and exact statuses; no output writes',t=>{
  const f=setup(t); const result=f.run('--journey',f.selection,'--dry-run')
  assert.equal(result.status,0,result.stderr)
  assert.deepEqual(JSON.parse(result.stdout).exchanges,[
    {method:'POST',path:'/orders',body:{label:'fixture'}},{method:'GET',path:'/orders/created%2F17'}
  ])
  assert.deepEqual(fs.readdirSync(f.dir).sort(),['api.json','journey.json'])
})

test('generated source parses and repeat generation preserves authored output',t=>{
  const f=setup(t); const result=f.run('--journey',f.selection,'--out',f.output)
  assert.equal(result.status,0,result.stderr)
  const file=JSON.parse(result.stdout).files[0]
  assert.equal(spawnSync(process.execPath,['--input-type=module','--check'],{input:fs.readFileSync(file)}).status,0)
  fs.writeFileSync(file,'custom thresholds')
  assert.notEqual(f.run('--journey',f.selection,'--out',f.output).status,0)
  assert.equal(fs.readFileSync(file,'utf8'),'custom thresholds')
})

for(const [name, mutate] of [
  ['401 cannot satisfy expected successful create', (s,j)=>{j.mock[0].status=401}],
  ['undeclared status', (s,j)=>{j.steps[0].expect=204}],
  ['required write fixture missing', (s,j)=>{delete j.steps[0].body}],
  ['capture unavailable', (s,j)=>{j.mock[0].response={}}],
  ['later capture cannot satisfy earlier step', (s,j)=>{j.steps.reverse()}],
  ['missing required query',s=>{s.paths['/orders'].post.parameters=[{in:'query',name:'tenant',required:true}]}],
  ['unresolved authentication',s=>{s.security=[{internal:['write']}]}],
  ['unresolved path owner',s=>{s.paths['/orders']={$ref:'orders.json'}}]
]) test(name,t=>{
  const s=structuredClone(spec),j=structuredClone(journey); mutate(s,j)
  const f=setup(t,s,j)
  assert.notEqual(f.run('--journey',f.selection,'--out',f.output).status,0)
  assert.equal(fs.existsSync(f.output),false)
})

test('reads real YAML including quoted keys, path metadata and inline responses',t=>{
  const f=setup(t)
  fs.writeFileSync(f.input+'.yaml',"openapi: '3.0.3'\npaths:\n  '/one':\n    parameters: []\n    head: {responses: {'204': {description: 'empty'}}}\n")
  const result=spawnSync(process.execPath,[cli,'--spec',f.input+'.yaml','--out',f.output],{encoding:'utf8'})
  assert.equal(result.status,0,result.stderr)
  assert.deepEqual(JSON.parse(result.stdout).operations,['HEAD /one'])
})

test('distinguishes aligned generator, service and mixed evidence',()=>{
  const base={start:'2026-11-18T07:00:00Z',end:'2026-11-18T07:01:00Z',targetRps:100,achievedRps:60,
    generatorCpuPct:95,serviceCpuPct:30,clientP95Ms:800,serverP95Ms:50,
    limits:{p95Ms:300,cpuPct:85,minDeliveryRatio:0.95}}
  assert.equal(diagnose(base).diagnosis,'GENERATOR_PRESSURE')
  assert.equal(diagnose({...base, generatorCpuPct:20,serviceCpuPct:92,serverP95Ms:400}).diagnosis,'SERVICE_PRESSURE')
  assert.equal(diagnose({...base,serviceCpuPct:92,serverP95Ms:400}).diagnosis,'MIXED_PRESSURE')
  assert.equal(diagnose({...base,generatorCpuPct:20}).diagnosis,'UNATTRIBUTED')
  assert.equal(diagnose({...base,generatorCpuPct:'95'}).status,'INSUFFICIENT_EVIDENCE')
  assert.equal(diagnose({...base,end:base.start}).status,'INSUFFICIENT_EVIDENCE')
})
