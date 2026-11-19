#!/usr/bin/env node
/** Attribute an observed load shortfall within a single aligned measurement window. */
import fs from 'node:fs'
import { pathToFileURL } from 'node:url'

export function diagnose(trace) {
  const {start, end, generatorCpuPct, serviceCpuPct, achievedRps, targetRps, clientP95Ms, serverP95Ms, limits} = trace || {}
  const number = n => typeof n === 'number' && Number.isFinite(n) && n >= 0
  const percent = n => number(n) && n <= 100
  if (!Number.isFinite(Date.parse(start)) || !Number.isFinite(Date.parse(end)) || Date.parse(start) >= Date.parse(end) ||
      !percent(generatorCpuPct) || !percent(serviceCpuPct) || !number(targetRps) || !targetRps || !number(achievedRps) ||
      !number(clientP95Ms) || !number(serverP95Ms) || !percent(limits?.cpuPct) || !limits.cpuPct ||
      !number(limits.minDeliveryRatio) || !limits.minDeliveryRatio || limits.minDeliveryRatio > 1 ||
      !number(limits.p95Ms) || !limits.p95Ms) return {status:'INSUFFICIENT_EVIDENCE'}
  const deliveryRatio = achievedRps / targetRps
  const degraded = clientP95Ms > limits.p95Ms || deliveryRatio < limits.minDeliveryRatio
  const generator = generatorCpuPct >= limits.cpuPct && deliveryRatio < limits.minDeliveryRatio
  const service = serviceCpuPct >= limits.cpuPct && serverP95Ms > limits.p95Ms
  let diagnosis = 'WITHIN_OBSERVED_BUDGET'
  if (degraded) {
    if (generator && service) diagnosis = 'MIXED_PRESSURE'
    else if (generator) diagnosis = 'GENERATOR_PRESSURE'
    else if (service) diagnosis = 'SERVICE_PRESSURE'
    else diagnosis = 'UNATTRIBUTED'
  }
  return {status:'OBSERVED', diagnosis, start, end, deliveryRatio, clientP95Ms, serverP95Ms}
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  try {
    const output = diagnose(JSON.parse(fs.readFileSync(process.argv[2], 'utf8').replace(/^\uFEFF/, '')))
    console.log(JSON.stringify(output, null, 2))
    if (output.status !== 'OBSERVED') process.exitCode = 1
  } catch (error) { console.error(error.message); process.exitCode = 1 }
}
