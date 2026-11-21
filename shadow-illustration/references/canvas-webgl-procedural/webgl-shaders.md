# WebGL2, GLSL Shaders & Full Context Recovery Engineering

## 1. Core Concepts
WebGL2 executes parallel vertex and fragment shaders on the GPU. Production reliability requires **zero-buffer full-screen triangles** for 2D fragment effects, **VAOs + hardware instancing** for repeated geometry, **portable GLSL math** that avoids mobile `NaN` artifacts, and **complete GPU resource reconstruction** across `webglcontextlost` and `webglcontextrestored`.

## 2. Technical Rules
- **Full-Screen Pass:** Render full-screen fragment shaders using a single 3-vertex triangle derived from `gl_VertexID` (`#version 300 es`) to eliminate diagonal quad seams and vertex buffer uploads.
- **Shader Precision & Safe Math:** Declare `precision highp float;` for UVs, time, and noise coordinates; clamp `pow(max(x, 0.0), y)` and guard `normalize(v + vec2(1e-6))` to prevent black `NaN` blocks on Safari/Metal.
- **Hardware Instancing & FBOs:** Bind attribute layouts inside a `WebGLVertexArrayObject`; batch repeated elements via `drawArraysInstanced` (`vertexAttribDivisor(loc, 1)`); use ping-pong `WebGLFramebuffer` pairs for trails, fluid advection, or bloom.
- **Mandatory Context Recovery:** On `webglcontextlost`, call `event.preventDefault()`, stop `rAF`, and show fallback UI. On `webglcontextrestored`, discard all invalidated GPU handles and rebuild shaders, programs, uniform locations, VAOs, buffers, textures, and FBOs from CPU-retained state.

## 3. Implementation Examples
```glsl
// Vertex Shader (#version 300 es) — Zero-buffer full-screen triangle
#version 300 es
out vec2 vUv;
void main() {
  vec2 pos = vec2((gl_VertexID == 1) ? 3.0 : -1.0, (gl_VertexID == 2) ? 3.0 : -1.0);
  vUv = pos * 0.5 + 0.5;
  gl_Position = vec4(pos, 0.0, 1.0);
}
```
```ts
// Context Loss & Full Restoration Lifecycle Wiring
canvas.addEventListener('webglcontextlost', (e: Event) => {
  e.preventDefault() // Mandatory: enables webglcontextrestored
  stopAnimationLoop()
  setFallbackVisible(true)
})
canvas.addEventListener('webglcontextrestored', () => {
  rebuildAllGpuResources() // Recompile shaders, relink program, recreate VAOs/buffers/textures
  setFallbackVisible(false)
  startAnimationLoop()
})
```

## 4. Best Practices
- Configure premultiplied alpha blending (`gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA)`) when initializing `{ alpha: true, premultipliedAlpha: true }` so edges blend cleanly over HTML backgrounds.
- Cache uniform locations (`gl.getUniformLocation`) during program link/restore — never query uniform locations inside the 60fps render loop.

## 5. Anti-patterns (WRONG vs RIGHT)
- **WRONG:** Only displaying a static fallback on `webglcontextlost` without calling `event.preventDefault()` or handling `webglcontextrestored`, or reusing old `WebGLProgram`/`WebGLBuffer` references after restore.
- **RIGHT:** Call `event.preventDefault()` and re-create every GPU resource from CPU state inside `webglcontextrestored`.
- **WRONG:** Issuing thousands of individual `gl.drawArrays` calls inside a JS loop for particles.
- **RIGHT:** Upload one interleaved instance buffer and issue a single `gl.drawArraysInstanced` call.

## 6. Production Considerations
- Test recovery deterministically via `gl.getExtension('WEBGL_lose_context')?.loseContext()` and `restoreContext()`.
- Explicitly call `deleteProgram`, `deleteShader`, `deleteBuffer`, `deleteVertexArray`, `deleteTexture`, and `deleteFramebuffer` in `dispose()` so SPA route changes never hit the browser's ~8–16 active WebGL context limit.
