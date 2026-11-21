import { createMulberry32 } from '../procedural-patterns/seeded-flow.js'

export class PooledParticleSystem {
  private readonly capacity: number
  private readonly x: Float32Array
  private readonly y: Float32Array
  private readonly vx: Float32Array
  private readonly vy: Float32Array
  private readonly age: Float32Array
  private readonly maxLife: Float32Array
  private readonly radius: Float32Array
  private readonly rand: () => number
  private activeCount = 0

  constructor(capacity = 120, seed = 20261121) {
    this.capacity = capacity
    this.x = new Float32Array(capacity)
    this.y = new Float32Array(capacity)
    this.vx = new Float32Array(capacity)
    this.vy = new Float32Array(capacity)
    this.age = new Float32Array(capacity)
    this.maxLife = new Float32Array(capacity)
    this.radius = new Float32Array(capacity)
    this.rand = createMulberry32(seed)
  }

  spawn(px: number, py: number): void {
    if (this.activeCount >= this.capacity) return
    const i = this.activeCount
    this.x[i] = px
    this.y[i] = py
    this.vx[i] = (this.rand() - 0.5) * 24
    this.vy[i] = -8 - this.rand() * 18
    this.age[i] = 0
    this.maxLife[i] = 2.5 + this.rand() * 3.0
    this.radius[i] = 1.5 + this.rand() * 2.0
    this.activeCount += 1
  }

  update(dtSeconds: number): void {
    const dt = Math.min(Math.max(dtSeconds, 0), 0.05)
    let i = 0
    while (i < this.activeCount) {
      const nextAge = (this.age[i] ?? 0) + dt
      const maxL = this.maxLife[i] ?? 1
      if (nextAge >= maxL) {
        this.kill(i)
        continue
      }
      this.age[i] = nextAge
      this.x[i] = (this.x[i] ?? 0) + (this.vx[i] ?? 0) * dt
      this.y[i] = (this.y[i] ?? 0) + (this.vy[i] ?? 0) * dt
      i += 1
    }
  }

  render(ctx: CanvasRenderingContext2D, width: number, height: number, fillStyle: string): void {
    const margin = 16
    ctx.fillStyle = fillStyle
    for (let i = 0; i < this.activeCount; i++) {
      const px = this.x[i] ?? 0
      const py = this.y[i] ?? 0
      if (px < -margin || px > width + margin || py < -margin || py > height + margin) {
        continue
      }
      const normAge = (this.age[i] ?? 0) / Math.max(this.maxLife[i] ?? 1, 0.001)
      const fadeIn = Math.min(normAge / 0.15, 1)
      const fadeOut = Math.min((1 - normAge) / 0.25, 1)
      ctx.globalAlpha = Math.max(0, Math.min(fadeIn, fadeOut)) * 0.45
      ctx.beginPath()
      ctx.arc(px, py, this.radius[i] ?? 2, 0, Math.PI * 2)
      ctx.fill()
    }
    ctx.globalAlpha = 1
  }

  private kill(index: number): void {
    const last = this.activeCount - 1
    if (index < 0 || index > last) return
    if (index !== last) {
      this.x[index] = this.x[last] ?? 0
      this.y[index] = this.y[last] ?? 0
      this.vx[index] = this.vx[last] ?? 0
      this.vy[index] = this.vy[last] ?? 0
      this.age[index] = this.age[last] ?? 0
      this.maxLife[index] = this.maxLife[last] ?? 1
      this.radius[index] = this.radius[last] ?? 2
    }
    this.activeCount = last
  }
}
