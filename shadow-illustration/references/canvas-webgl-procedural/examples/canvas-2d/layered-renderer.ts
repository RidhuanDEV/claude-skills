export interface CanvasThemePalette {
  readonly background: string
  readonly accent: string
  readonly stroke: string
}

export interface LayeredRendererOptions {
  readonly maxDpr?: number
  readonly reducedMotion?: boolean
  readonly palette: CanvasThemePalette
}

export class LayeredCanvasRenderer {
  private readonly canvas: HTMLCanvasElement
  private readonly ctx: CanvasRenderingContext2D
  private readonly staticLayer: HTMLCanvasElement
  private readonly staticCtx: CanvasRenderingContext2D
  private readonly maxDpr: number

  private palette: CanvasThemePalette
  private reducedMotion: boolean
  private width = 0
  private height = 0
  private dpr = 1
  private elapsed = 0
  private lastTime = 0
  private visible = true
  private rafId: number | null = null
  private pointerX = 0.5
  private pointerY = 0.5
  private smoothX = 0.5
  private smoothY = 0.5

  constructor(canvas: HTMLCanvasElement, options: LayeredRendererOptions) {
    const ctx = canvas.getContext('2d')
    if (!ctx) throw new Error('Canvas 2D context unavailable')
    const staticLayer = document.createElement('canvas')
    const staticCtx = staticLayer.getContext('2d')
    if (!staticCtx) throw new Error('Offscreen Canvas 2D context unavailable')

    this.canvas = canvas
    this.ctx = ctx
    this.staticLayer = staticLayer
    this.staticCtx = staticCtx
    this.maxDpr = options.maxDpr ?? 2
    this.palette = options.palette
    this.reducedMotion = options.reducedMotion ?? false
  }

  resize(cssWidth: number, cssHeight: number, devicePixelRatio: number): void {
    this.width = Math.max(1, Math.round(cssWidth))
    this.height = Math.max(1, Math.round(cssHeight))
    this.dpr = Math.min(Math.max(devicePixelRatio || 1, 1), this.maxDpr)

    const backingW = Math.round(this.width * this.dpr)
    const backingH = Math.round(this.height * this.dpr)
    this.canvas.width = backingW
    this.canvas.height = backingH
    this.staticLayer.width = backingW
    this.staticLayer.height = backingH

    this.rebuildStaticLayer()
    this.render()
  }

  setPalette(palette: CanvasThemePalette): void {
    this.palette = palette
    this.rebuildStaticLayer()
    this.render()
  }

  setPointer(normX: number, normY: number): void {
    this.pointerX = Math.min(Math.max(normX, 0), 1)
    this.pointerY = Math.min(Math.max(normY, 0), 1)
  }

  setReducedMotion(reduced: boolean): void {
    this.reducedMotion = reduced
    if (reduced) {
      this.stopLoop()
      this.render()
    } else if (this.visible) {
      this.startLoop()
    }
  }

  setVisibility(isVisible: boolean): void {
    this.visible = isVisible
    if (!isVisible) {
      this.stopLoop()
      return
    }
    this.lastTime = performance.now()
    if (!this.reducedMotion) {
      this.startLoop()
    }
  }

  start(): void {
    this.lastTime = performance.now()
    if (this.reducedMotion) {
      this.render()
      return
    }
    this.startLoop()
  }

  renderAt(timeSeconds: number): void {
    this.elapsed = timeSeconds
    this.render()
  }

  dispose(): void {
    this.stopLoop()
    this.staticLayer.width = 0
    this.staticLayer.height = 0
  }

  private rebuildStaticLayer(): void {
    const sctx = this.staticCtx
    sctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0)
    sctx.fillStyle = this.palette.background
    sctx.fillRect(0, 0, this.width, this.height)

    const grad = sctx.createRadialGradient(
      this.width * 0.72,
      this.height * 0.34,
      12,
      this.width * 0.72,
      this.height * 0.34,
      Math.max(this.width, this.height) * 0.55,
    )
    grad.addColorStop(0, this.palette.accent)
    grad.addColorStop(1, 'transparent')
    sctx.globalAlpha = 0.16
    sctx.fillStyle = grad
    sctx.fillRect(0, 0, this.width, this.height)
    sctx.globalAlpha = 1
  }

  private startLoop(): void {
    if (this.rafId !== null) return
    this.lastTime = performance.now()
    const tick = (now: number): void => {
      const rawDt = (now - this.lastTime) / 1000
      this.lastTime = now
      const dt = Math.min(Math.max(rawDt, 0), 0.05)
      this.update(dt)
      this.render()
      this.rafId = requestAnimationFrame(tick)
    }
    this.rafId = requestAnimationFrame(tick)
  }

  private stopLoop(): void {
    if (this.rafId !== null) {
      cancelAnimationFrame(this.rafId)
      this.rafId = null
    }
  }

  private update(dt: number): void {
    this.elapsed += dt
    const alpha = 1 - Math.exp(-6 * dt)
    this.smoothX += (this.pointerX - this.smoothX) * alpha
    this.smoothY += (this.pointerY - this.smoothY) * alpha
  }

  private render(): void {
    const ctx = this.ctx
    ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0)
    ctx.drawImage(this.staticLayer, 0, 0, this.width, this.height)

    ctx.strokeStyle = this.palette.stroke
    ctx.lineWidth = 1.25
    ctx.globalAlpha = 0.35
    ctx.beginPath()
    const rows = 4
    const steps = 16
    for (let r = 0; r < rows; r++) {
      const baseY = this.height * (0.58 + r * 0.09)
      for (let i = 0; i <= steps; i++) {
        const u = i / steps
        const x = u * this.width
        const wave = Math.sin(u * 5.2 + this.elapsed * 0.55 + r * 0.9 + this.smoothX * 1.4) * 14
        const y = baseY + wave + (this.smoothY - 0.5) * 10
        if (i === 0) ctx.moveTo(x, y)
        else ctx.lineTo(x, y)
      }
    }
    ctx.stroke()
    ctx.globalAlpha = 1
  }
}
