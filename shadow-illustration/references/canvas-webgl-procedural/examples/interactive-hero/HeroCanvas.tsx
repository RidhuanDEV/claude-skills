import { useEffect, useRef } from 'react'
import { LayeredCanvasRenderer } from '../canvas-2d/layered-renderer.js'
import type { CanvasThemePalette } from '../canvas-2d/layered-renderer.js'

function readThemePalette(): CanvasThemePalette {
  const style = getComputedStyle(document.documentElement)
  const background = style.getPropertyValue('--bg').trim() || '#f8fafc'
  const accent = style.getPropertyValue('--primary').trim() || '#1d4ed8'
  const stroke = style.getPropertyValue('--border').trim() || '#64748b'
  return { background, accent, stroke }
}

export function HeroCanvas() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const motionMedia = window.matchMedia('(prefers-reduced-motion: reduce)')
    const renderer = new LayeredCanvasRenderer(canvas, {
      maxDpr: 2,
      reducedMotion: motionMedia.matches,
      palette: readThemePalette(),
    })

    let cachedRect = canvas.getBoundingClientRect()
    renderer.resize(cachedRect.width, cachedRect.height, window.devicePixelRatio || 1)
    renderer.start()

    const resizeObserver = new ResizeObserver((entries) => {
      const entry = entries[0]
      if (!entry) return
      cachedRect = canvas.getBoundingClientRect()
      renderer.resize(entry.contentRect.width, entry.contentRect.height, window.devicePixelRatio || 1)
    })
    resizeObserver.observe(canvas)

    const intersectionObserver = new IntersectionObserver((entries) => {
      const entry = entries[0]
      if (entry) renderer.setVisibility(entry.isIntersecting && !document.hidden)
    })
    intersectionObserver.observe(canvas)

    const onVisibilityChange = (): void => {
      renderer.setVisibility(!document.hidden)
    }
    const onMotionChange = (event: MediaQueryListEvent): void => {
      renderer.setReducedMotion(event.matches)
    }
    const onPointerMove = (event: PointerEvent): void => {
      if (cachedRect.width <= 0 || cachedRect.height <= 0) return
      const normX = (event.clientX - cachedRect.left) / cachedRect.width
      const normY = (event.clientY - cachedRect.top) / cachedRect.height
      renderer.setPointer(normX, normY)
    }

    document.addEventListener('visibilitychange', onVisibilityChange)
    motionMedia.addEventListener('change', onMotionChange)
    window.addEventListener('pointermove', onPointerMove, { passive: true })

    return () => {
      resizeObserver.disconnect()
      intersectionObserver.disconnect()
      document.removeEventListener('visibilitychange', onVisibilityChange)
      motionMedia.removeEventListener('change', onMotionChange)
      window.removeEventListener('pointermove', onPointerMove)
      renderer.dispose()
    }
  }, [])

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      tabIndex={-1}
      style={{
        position: 'absolute',
        inset: 0,
        width: '100%',
        height: '100%',
        pointerEvents: 'none',
      }}
    />
  )
}
