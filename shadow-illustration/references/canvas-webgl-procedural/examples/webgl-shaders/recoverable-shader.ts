export interface ShaderRendererCallbacks {
  readonly onContextLost?: () => void
  readonly onContextRestored?: () => void
}

const VERT_SRC = `#version 300 es
out vec2 vUv;
void main() {
  vec2 pos = vec2((gl_VertexID == 1) ? 3.0 : -1.0, (gl_VertexID == 2) ? 3.0 : -1.0);
  vUv = pos * 0.5 + 0.5;
  gl_Position = vec4(pos, 0.0, 1.0);
}
`

const FRAG_SRC = `#version 300 es
precision highp float;
in vec2 vUv;
uniform float uTime;
uniform vec2 uResolution;
uniform vec2 uPointer;
uniform vec3 uBaseColor;
uniform vec3 uAccentColor;
out vec4 fragColor;

void main() {
  vec2 aspect = vec2(uResolution.x / max(uResolution.y, 1.0), 1.0);
  vec2 p = (vUv - vec2(0.7, 0.5)) * aspect;
  float wave = sin(p.x * 4.5 + uTime * 0.4) * cos(p.y * 3.5 - uTime * 0.3);
  float dist = length(p - (uPointer - 0.5) * 0.25);
  float glow = pow(max(1.0 - dist * 1.15, 0.0), 2.2) * 0.22;
  vec3 col = mix(uBaseColor, uAccentColor, clamp(glow + wave * 0.05, 0.0, 0.35));
  fragColor = vec4(col, 1.0);
}
`

export class RecoverableWebGlShader {
  private readonly canvas: HTMLCanvasElement
  private readonly gl: WebGL2RenderingContext
  private readonly callbacks: ShaderRendererCallbacks

  private program: WebGLProgram | null = null
  private vao: WebGLVertexArrayObject | null = null
  private uTimeLoc: WebGLUniformLocation | null = null
  private uResLoc: WebGLUniformLocation | null = null
  private uPtrLoc: WebGLUniformLocation | null = null
  private uBaseLoc: WebGLUniformLocation | null = null
  private uAccLoc: WebGLUniformLocation | null = null

  private isLost = false
  private rafId: number | null = null
  private lastTime = 0
  private elapsed = 0
  private width = 1
  private height = 1
  private pointer: readonly [number, number] = [0.5, 0.5]
  private baseColor: readonly [number, number, number] = [0.06, 0.09, 0.16]
  private accentColor: readonly [number, number, number] = [0.18, 0.38, 0.86]

  private readonly handleContextLost = (event: Event): void => {
    event.preventDefault() // Critical: allows browser to dispatch webglcontextrestored
    this.isLost = true
    this.stop()
    this.callbacks.onContextLost?.()
  }

  private readonly handleContextRestored = (): void => {
    this.isLost = false
    this.rebuildGpuResources()
    this.lastTime = performance.now()
    this.callbacks.onContextRestored?.()
    this.render()
  }

  constructor(canvas: HTMLCanvasElement, callbacks: ShaderRendererCallbacks = {}) {
    const gl = canvas.getContext('webgl2', { alpha: true, premultipliedAlpha: true, antialias: false })
    if (!gl) throw new Error('WebGL2 unavailable')
    this.canvas = canvas
    this.gl = gl
    this.callbacks = callbacks

    this.canvas.addEventListener('webglcontextlost', this.handleContextLost)
    this.canvas.addEventListener('webglcontextrestored', this.handleContextRestored)
    this.rebuildGpuResources()
  }

  resize(cssWidth: number, cssHeight: number, dpr: number): void {
    const safeDpr = Math.min(Math.max(dpr || 1, 1), 1.5)
    this.width = Math.max(1, Math.round(cssWidth * safeDpr))
    this.height = Math.max(1, Math.round(cssHeight * safeDpr))
    this.canvas.width = this.width
    this.canvas.height = this.height
    if (!this.isLost) {
      this.gl.viewport(0, 0, this.width, this.height)
      this.render()
    }
  }

  setPointer(normX: number, normY: number): void {
    this.pointer = [normX, 1 - normY]
  }

  start(): void {
    if (this.rafId !== null || this.isLost) return
    this.lastTime = performance.now()
    const loop = (now: number): void => {
      const dt = Math.min(Math.max((now - this.lastTime) / 1000, 0), 0.05)
      this.lastTime = now
      this.elapsed += dt
      this.render()
      this.rafId = requestAnimationFrame(loop)
    }
    this.rafId = requestAnimationFrame(loop)
  }

  stop(): void {
    if (this.rafId !== null) {
      cancelAnimationFrame(this.rafId)
      this.rafId = null
    }
  }

  renderAt(timeSeconds: number): void {
    this.elapsed = timeSeconds
    this.render()
  }

  dispose(): void {
    this.stop()
    this.canvas.removeEventListener('webglcontextlost', this.handleContextLost)
    this.canvas.removeEventListener('webglcontextrestored', this.handleContextRestored)
    if (!this.isLost) {
      if (this.vao) this.gl.deleteVertexArray(this.vao)
      if (this.program) this.gl.deleteProgram(this.program)
    }
    this.vao = null
    this.program = null
  }

  private rebuildGpuResources(): void {
    const gl = this.gl
    const vs = this.compileShader(gl.VERTEX_SHADER, VERT_SRC)
    const fs = this.compileShader(gl.FRAGMENT_SHADER, FRAG_SRC)
    const prog = gl.createProgram()
    if (!prog) throw new Error('Failed creating WebGLProgram')
    gl.attachShader(prog, vs)
    gl.attachShader(prog, fs)
    gl.linkProgram(prog)
    gl.deleteShader(vs)
    gl.deleteShader(fs)

    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) {
      const info = gl.getProgramInfoLog(prog) ?? 'Unknown link error'
      gl.deleteProgram(prog)
      throw new Error(`WebGLProgram link failed: ${info}`)
    }

    this.program = prog
    this.vao = gl.createVertexArray()
    this.uTimeLoc = gl.getUniformLocation(prog, 'uTime')
    this.uResLoc = gl.getUniformLocation(prog, 'uResolution')
    this.uPtrLoc = gl.getUniformLocation(prog, 'uPointer')
    this.uBaseLoc = gl.getUniformLocation(prog, 'uBaseColor')
    this.uAccLoc = gl.getUniformLocation(prog, 'uAccentColor')
    gl.viewport(0, 0, this.width, this.height)
  }

  private compileShader(type: number, source: string): WebGLShader {
    const gl = this.gl
    const shader = gl.createShader(type)
    if (!shader) throw new Error('Failed creating WebGLShader')
    gl.shaderSource(shader, source)
    gl.compileShader(shader)
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
      const info = gl.getShaderInfoLog(shader) ?? 'Unknown shader compile error'
      gl.deleteShader(shader)
      throw new Error(`Shader compile failed: ${info}`)
    }
    return shader
  }

  private render(): void {
    if (this.isLost || !this.program) return
    const gl = this.gl
    gl.useProgram(this.program)
    gl.bindVertexArray(this.vao)
    gl.uniform1f(this.uTimeLoc, this.elapsed)
    gl.uniform2f(this.uResLoc, this.width, this.height)
    gl.uniform2f(this.uPtrLoc, this.pointer[0], this.pointer[1])
    gl.uniform3f(this.uBaseLoc, this.baseColor[0], this.baseColor[1], this.baseColor[2])
    gl.uniform3f(this.uAccLoc, this.accentColor[0], this.accentColor[1], this.accentColor[2])
    gl.drawArrays(gl.TRIANGLES, 0, 3)
  }
}
