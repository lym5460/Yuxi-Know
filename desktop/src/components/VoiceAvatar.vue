<template>
  <div ref="containerRef" class="voice-avatar-container">
    <canvas ref="canvasRef" />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  audioLevel: { type: Number, default: 0 },
  status: { type: String, default: 'idle' }
})

const containerRef = ref(null)
const canvasRef = ref(null)

let ctx = null
let w = 0, h = 0
let animId = null
let resizeObserver = null
let smoothLevel = 0
let blinkProg = 0
let nextBlink = 3
let particles = []

const C1 = [0, 212, 255]   // 青
const C2 = [120, 80, 255]   // 紫
const C3 = [255, 56, 160]   // 粉（error）
const BODY = [14, 22, 40]   // 机体暗色
const EDGE = [0, 180, 220]  // 边缘线

function lerp(a, b, t) { return a + (b - a) * t }
function mix(c1, c2, t) { return c1.map((v, i) => lerp(v, c2[i], t)) }
function rgba(c, a) { return `rgba(${c[0]|0},${c[1]|0},${c[2]|0},${a})` }

function glow(color, blur) { ctx.shadowColor = color; ctx.shadowBlur = blur }
function noGlow() { ctx.shadowBlur = 0 }

// 绘制发光描边路径
function strokeGlow(color, lineW, blur) {
  ctx.strokeStyle = color
  ctx.lineWidth = lineW
  if (blur) glow(color, blur)
  ctx.stroke()
  noGlow()
}

// 绘制填充+描边的多边形
function drawPoly(points, fill, stroke, lineW, glowColor, glowSize) {
  ctx.beginPath()
  points.forEach((p, i) => i === 0 ? ctx.moveTo(p[0], p[1]) : ctx.lineTo(p[0], p[1]))
  ctx.closePath()
  if (fill) { ctx.fillStyle = fill; ctx.fill() }
  if (stroke) {
    ctx.strokeStyle = stroke
    ctx.lineWidth = lineW || 1.5
    if (glowColor) glow(glowColor, glowSize || 6)
    ctx.stroke()
    noGlow()
  }
}

function initParticles() {
  particles = Array.from({ length: 20 }, () => ({
    x: Math.random(), y: Math.random(),
    vx: (Math.random() - 0.5) * 0.3, vy: -0.1 - Math.random() * 0.3,
    size: 0.5 + Math.random() * 1.5, life: Math.random()
  }))
}

function resize() {
  const el = containerRef.value, canvas = canvasRef.value
  if (!el || !canvas) return
  const dpr = window.devicePixelRatio || 1
  w = el.clientWidth; h = el.clientHeight
  canvas.width = w * dpr; canvas.height = h * dpr
  canvas.style.width = w + 'px'; canvas.style.height = h + 'px'
  ctx = canvas.getContext('2d')
  ctx.scale(dpr, dpr)
  initParticles()
}

// 圆角矩形辅助
function roundRect(x, y, w, h, r) {
  ctx.beginPath()
  ctx.moveTo(x + r, y)
  ctx.lineTo(x + w - r, y)
  ctx.arcTo(x + w, y, x + w, y + r, r)
  ctx.lineTo(x + w, y + h - r)
  ctx.arcTo(x + w, y + h, x + w - r, y + h, r)
  ctx.lineTo(x + r, y + h)
  ctx.arcTo(x, y + h, x, y + h - r, r)
  ctx.lineTo(x, y + r)
  ctx.arcTo(x, y, x + r, y, r)
  ctx.closePath()
}

function render(timestamp) {
  animId = requestAnimationFrame(render)
  if (!ctx) return
  const t = timestamp / 1000
  ctx.clearRect(0, 0, w, h)

  const cx = w / 2
  const cy = h * 0.5
  const u = Math.min(w, h) * 0.038

  const isSpeaking = props.status === 'speaking'
  const isListening = props.status === 'listening'
  const isActive = isSpeaking || isListening || props.status === 'processing'
  const synthLevel = isSpeaking
    ? 0.35 + Math.sin(t * 5.2) * 0.15 + Math.sin(t * 7.8) * 0.1
    : props.audioLevel
  smoothLevel += (synthLevel - smoothLevel) * (synthLevel > smoothLevel ? 0.3 : 0.08)
  const al = smoothLevel
  const breath = 1 + Math.sin(t * 1.0) * 0.006
  const sc = mix(C1, C2, isSpeaking ? al * 0.5 : 0)

  // 头部尺寸
  const headW = u * 9
  const headH = u * 8
  const headR = u * 1.8
  const headX = cx - headW / 2
  const headY = cy - headH / 2 - u * 1

  // =============================================
  // 1. 背景辉光
  // =============================================
  // idle 时也有呼吸感的背景辉光
  const idlePulse = 0.5 + Math.sin(t * 1.5) * 0.5  // 0~1 缓慢呼吸
  const bgCenter = isActive ? 0.12 + al * 0.15 : 0.06 + idlePulse * 0.04
  const bgMid = isActive ? 0.04 + al * 0.05 : 0.02 + idlePulse * 0.015
  const gr = ctx.createRadialGradient(cx, cy, u * 2, cx, cy, u * 18)
  gr.addColorStop(0, rgba(sc, bgCenter))
  gr.addColorStop(0.4, rgba(sc, bgMid))
  gr.addColorStop(1, 'rgba(0,0,0,0)')
  ctx.fillStyle = gr
  ctx.fillRect(0, 0, w, h)

  // 脉冲环（活跃时快速扩散，idle 时缓慢呼吸）
  const ringCount = isActive ? 4 : 2
  const ringSpeed = isActive ? 0.4 : 0.15
  const ringAlpha = isActive ? 0.12 + al * 0.18 : 0.04 + idlePulse * 0.03
  for (let i = 0; i < ringCount; i++) {
    const ph = (t * ringSpeed + i / ringCount) % 1
    const rr = u * (4 + ph * 14)
    ctx.beginPath(); ctx.arc(cx, cy, rr, 0, Math.PI * 2)
    ctx.strokeStyle = rgba(sc, (1 - ph) * ringAlpha)
    ctx.lineWidth = 2 - ph * 1.5; ctx.stroke()
  }

  // =============================================
  // 2. 耳朵（圆角方形，画在头部下方微露）
  // =============================================
  for (const s of [-1, 1]) {
    const earW = u * 1.4
    const earH = u * 2.4
    const earX = cx + s * (headW / 2) - earW / 2 + s * u * 0.5
    const earY = cy - u * 1 - earH / 2
    roundRect(earX, earY, earW, earH, u * 0.4)
    ctx.fillStyle = rgba(BODY, 0.9); ctx.fill()
    glow(rgba(sc, 0.2), 2 + al * 2)
    ctx.strokeStyle = rgba(EDGE, 0.18 + al * 0.1)
    ctx.lineWidth = 1; ctx.stroke(); noGlow()
  }

  // =============================================
  // 3. 头部（🤖 风格方头圆角）
  // =============================================
  roundRect(headX, headY * breath, headW, headH, headR)
  const hGr = ctx.createLinearGradient(headX, headY, headX, headY + headH)
  hGr.addColorStop(0, rgba([20, 30, 50], 0.95))
  hGr.addColorStop(1, rgba(BODY, 0.92))
  ctx.fillStyle = hGr; ctx.fill()
  glow(rgba(sc, 0.4), 5 + al * 6)
  ctx.strokeStyle = rgba(EDGE, 0.3 + al * 0.2)
  ctx.lineWidth = 2; ctx.stroke(); noGlow()

  // =============================================
  // 6. 天线
  // =============================================
  const antX = cx
  const antBaseY = headY * breath
  const antTopY = antBaseY - u * 3
  // 天线杆
  ctx.beginPath()
  ctx.moveTo(antX, antBaseY); ctx.lineTo(antX, antTopY + u * 0.8)
  ctx.strokeStyle = rgba(EDGE, 0.3 + al * 0.2)
  ctx.lineWidth = u * 0.35; ctx.stroke()
  // 天线球（发光）
  const antPulse = 0.5 + Math.sin(t * 3) * 0.3
  ctx.beginPath(); ctx.arc(antX, antTopY, u * 0.6, 0, Math.PI * 2)
  ctx.fillStyle = rgba(sc, (0.4 + al * 0.4) * (isActive ? 1 : antPulse))
  glow(rgba(sc, 0.8), 8 + al * 12); ctx.fill(); noGlow()
  // 天线底座
  roundRect(antX - u * 0.8, antBaseY - u * 0.3, u * 1.6, u * 0.6, u * 0.2)
  ctx.fillStyle = rgba(BODY, 0.9); ctx.fill()
  ctx.strokeStyle = rgba(EDGE, 0.2); ctx.lineWidth = 1; ctx.stroke()

  // =============================================
  // 7. 眼睛（可爱卡通风格）
  // =============================================
  const eyeY = headY + headH * 0.4
  const eyeSpacing = u * 2.2
  const eyeR = u * 1.5

  if (t > nextBlink) { blinkProg = 1; nextBlink = t + 2.5 + Math.random() * 4 }
  if (blinkProg > 0) blinkProg = Math.max(0, blinkProg - 0.12)
  const eyeOpen = 1 - blinkProg

  for (const s of [-1, 1]) {
    const ex = cx + s * eyeSpacing
    const ey = eyeY

    if (eyeOpen < 0.15) {
      // 眨眼：画一条弧线
      ctx.beginPath()
      ctx.arc(ex, ey, eyeR * 0.6, 0, Math.PI)
      ctx.strokeStyle = rgba(sc, 0.5)
      ctx.lineWidth = u * 0.3; ctx.stroke()
      continue
    }

    // 眼球底色（柔和渐变）
    ctx.beginPath(); ctx.arc(ex, ey, eyeR, 0, Math.PI * 2)
    const eyeBg = ctx.createRadialGradient(ex, ey - u * 0.3, eyeR * 0.1, ex, ey, eyeR)
    eyeBg.addColorStop(0, rgba([50, 70, 100], 0.85 * eyeOpen))
    eyeBg.addColorStop(1, rgba([20, 35, 55], 0.9 * eyeOpen))
    ctx.fillStyle = eyeBg; ctx.fill()
    glow(rgba(sc, 0.3), 3 + al * 4)
    ctx.strokeStyle = rgba(sc, 0.2 + al * 0.15)
    ctx.lineWidth = 1.2; ctx.stroke(); noGlow()

    // 瞳孔（大而圆，可爱感的关键）
    const pupilR = eyeR * 0.55 * eyeOpen
    ctx.beginPath(); ctx.arc(ex, ey, pupilR, 0, Math.PI * 2)
    const pupilGr = ctx.createRadialGradient(ex, ey, pupilR * 0.2, ex, ey, pupilR)
    pupilGr.addColorStop(0, rgba(sc, 0.9))
    pupilGr.addColorStop(0.6, rgba(sc, 0.5 + al * 0.2))
    pupilGr.addColorStop(1, rgba(sc, 0.2))
    ctx.fillStyle = pupilGr
    glow(rgba(sc, 0.5), 4 + al * 6); ctx.fill(); noGlow()

    // 大高光（左上方，可爱感核心）
    const hlR = eyeR * 0.3
    ctx.beginPath(); ctx.arc(ex - u * 0.35, ey - u * 0.35, hlR, 0, Math.PI * 2)
    ctx.fillStyle = rgba([255, 255, 255], 0.55 * eyeOpen); ctx.fill()

    // 小高光（右下方）
    ctx.beginPath(); ctx.arc(ex + u * 0.25, ey + u * 0.2, hlR * 0.35, 0, Math.PI * 2)
    ctx.fillStyle = rgba([255, 255, 255], 0.35 * eyeOpen); ctx.fill()
  }

  // =============================================
  // 9. 嘴巴（LED 栅格条 🤖 风格）
  // =============================================
  const mouthY = headY + headH * 0.72
  const mouthW = u * 4.5
  const mouthH = u * 1.8
  const mR = u * 0.5

  // 嘴巴背景
  roundRect(cx - mouthW / 2, mouthY - mouthH / 2, mouthW, mouthH, mR)
  ctx.fillStyle = rgba([5, 10, 20], 0.7); ctx.fill()
  ctx.strokeStyle = rgba(EDGE, 0.15 + al * 0.1)
  ctx.lineWidth = 1; ctx.stroke()

  // LED 横条
  const barCount = 5
  const barH = mouthH / (barCount * 2 - 1)
  const barPad = u * 0.4
  for (let i = 0; i < barCount; i++) {
    const by = mouthY - mouthH / 2 + barH * 0.5 + i * barH * 2
    let barOp = 0.15
    let barW = mouthW - barPad * 2
    if (isSpeaking) {
      const env = 1 - Math.abs(i - barCount / 2) / (barCount / 2) * 0.5
      barOp = 0.2 + al * 0.7 * env * (0.4 + Math.sin(t * 10 + i * 1.5) * 0.6)
      barW *= 0.6 + 0.4 * (0.5 + Math.sin(t * 8 + i * 2) * 0.5) * al
    } else if (isListening && al > 0.05) {
      barOp = 0.15 + al * 0.4 * (0.5 + Math.sin(t * 5 + i * 1.2) * 0.5)
    }
    roundRect(cx - barW / 2, by - barH * 0.4, barW, barH * 0.8, u * 0.15)
    ctx.fillStyle = rgba(sc, barOp)
    if (barOp > 0.25) glow(rgba(sc, 0.5), 3 + al * 6)
    ctx.fill(); noGlow()
  }

  // =============================================
  // 10. 面部装饰线
  // =============================================
  // 额头横线
  ctx.beginPath()
  ctx.moveTo(headX + u * 1.5, headY + u * 1.2)
  ctx.lineTo(headX + headW - u * 1.5, headY + u * 1.2)
  ctx.strokeStyle = rgba(sc, 0.08 + al * 0.06)
  ctx.lineWidth = 1; ctx.stroke()
  // 面颊线
  for (const s of [-1, 1]) {
    ctx.beginPath()
    ctx.moveTo(cx + s * (headW / 2 - u * 0.8), eyeY + u * 1.5)
    ctx.lineTo(cx + s * (headW / 2 - u * 1.2), mouthY + u * 0.5)
    ctx.strokeStyle = rgba(sc, 0.06 + al * 0.06)
    ctx.lineWidth = 1; ctx.stroke()
  }

  // =============================================
  // 9. 粒子
  // =============================================
  for (const p of particles) {
    p.y -= 0.002 + al * 0.003
    p.x += p.vx * 0.001
    if (p.y < -0.1) { p.y = 1.1; p.x = 0.3 + Math.random() * 0.4 }
    p.life = (p.life + 0.003) % 1
    const pop = Math.sin(p.life * Math.PI) * (0.2 + al * 0.35)
    ctx.beginPath(); ctx.arc(p.x * w, p.y * h, p.size * (1 + al * 0.5), 0, Math.PI * 2)
    ctx.fillStyle = rgba(sc, pop); ctx.fill()
  }

  // 扫描线
  const scanPh = (t * 0.25) % 1
  const headBot = headY + headH
  const scanSY = (headY - u * 3) + scanPh * (headBot - headY + u * 6)
  ctx.beginPath()
  ctx.moveTo(cx - u * 6, scanSY); ctx.lineTo(cx + u * 6, scanSY)
  ctx.strokeStyle = rgba(sc, 0.03 + al * 0.03)
  ctx.lineWidth = 1; ctx.stroke()

  // =============================================
  // 10. 状态文字
  // =============================================
  if (props.status !== 'idle') {
    const labels = {
      connecting: '系统连接中…', listening: '语音接收中',
      processing: 'AI 思考中…', speaking: '语音输出中', error: '连接异常'
    }
    const label = labels[props.status] || ''
    if (label) {
      ctx.font = `${u * 1.1}px -apple-system, sans-serif`
      ctx.textAlign = 'center'
      ctx.fillStyle = rgba(props.status === 'error' ? C3 : sc, 0.5 + al * 0.3)
      glow(rgba(sc, 0.4), 6)
      ctx.fillText(label, cx, headY + headH + u * 2)
      noGlow()
    }
  }
}

onMounted(() => {
  resize()
  animId = requestAnimationFrame(render)
  window.addEventListener('resize', resize)
  // 监听容器尺寸变化（侧边栏收起/展开时触发）
  if (containerRef.value) {
    resizeObserver = new ResizeObserver(resize)
    resizeObserver.observe(containerRef.value)
  }
})

onUnmounted(() => {
  if (animId) cancelAnimationFrame(animId)
  window.removeEventListener('resize', resize)
  if (resizeObserver) { resizeObserver.disconnect(); resizeObserver = null }
})
</script>

<style lang="less" scoped>
.voice-avatar-container {
  width: 100%;
  height: 100%;
  position: relative;
  canvas {
    display: block;
    width: 100%;
    height: 100%;
  }
}
</style>
