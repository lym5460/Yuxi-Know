<template>
  <div ref="containerRef" class="audio-visualizer" />
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import * as THREE from 'three'

const props = defineProps({
  audioLevel: { type: Number, default: 0 },
  active: { type: Boolean, default: false },
  barCount: { type: Number, default: 64 }
})

const containerRef = ref(null)
let scene, camera, renderer, bars, glowBars
let animFrameId = null
let currentLevels = []
let smoothLevel = 0

// 频谱色表：青 → 蓝 → 紫 → 粉
const spectrumColors = [
  [0, 0.83, 1],     // #00d4ff 青
  [0, 0.55, 1],     // #008cff 蓝
  [0.4, 0.3, 1],    // #664dff 紫蓝
  [0.7, 0.2, 1],    // #b333ff 紫
  [1, 0.2, 0.7],    // #ff33b3 粉紫
  [1, 0.35, 0.55],  // #ff598c 粉
]

function lerpColor(colors, t) {
  const idx = t * (colors.length - 1)
  const i = Math.floor(idx)
  const f = idx - i
  const c1 = colors[Math.min(i, colors.length - 1)]
  const c2 = colors[Math.min(i + 1, colors.length - 1)]
  return [c1[0] + (c2[0] - c1[0]) * f, c1[1] + (c2[1] - c1[1]) * f, c1[2] + (c2[2] - c1[2]) * f]
}

let mirrorBars, tipDots, bgGlow
let latestAudioLevel = 0
let latestActive = false

function init() {
  const el = containerRef.value
  if (!el) return
  const w = el.clientWidth
  const h = el.clientHeight
  if (w === 0 || h === 0) return

  scene = new THREE.Scene()
  camera = new THREE.OrthographicCamera(-w / 2, w / 2, h / 2, -h / 2, 0.1, 100)
  camera.position.z = 10

  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
  renderer.setSize(w, h)
  renderer.setPixelRatio(window.devicePixelRatio)
  renderer.setClearColor(0x000000, 0)
  el.appendChild(renderer.domElement)

  currentLevels = new Array(props.barCount).fill(0)

  const barW = Math.max(2, (w * 0.92) / props.barCount * 0.6)
  const gap = barW * 0.5
  const totalW = props.barCount * (barW + gap) - gap
  const startX = -totalW / 2

  bars = []
  glowBars = []
  mirrorBars = []
  tipDots = []

  // 背景辉光
  const bgGeo = new THREE.PlaneGeometry(w, h)
  const bgMat = new THREE.MeshBasicMaterial({ color: 0x00d4ff, transparent: true, opacity: 0 })
  bgGlow = new THREE.Mesh(bgGeo, bgMat)
  bgGlow.position.z = -1
  scene.add(bgGlow)

  for (let i = 0; i < props.barCount; i++) {
    const xPos = startX + i * (barW + gap) + barW / 2

    // 上方主条
    const geo = new THREE.PlaneGeometry(barW, 1)
    const mat = new THREE.MeshBasicMaterial({ color: 0x00d4ff, transparent: true, opacity: 0.9 })
    const mesh = new THREE.Mesh(geo, mat)
    mesh.position.set(xPos, 0, 0)
    scene.add(mesh)
    bars.push(mesh)

    // 辉光层
    const gGeo = new THREE.PlaneGeometry(barW + 4, 1)
    const gMat = new THREE.MeshBasicMaterial({ color: 0x00d4ff, transparent: true, opacity: 0 })
    const gMesh = new THREE.Mesh(gGeo, gMat)
    gMesh.position.set(xPos, 0, -0.1)
    scene.add(gMesh)
    glowBars.push(gMesh)

    // 下方镜像条（半透明）
    const mGeo = new THREE.PlaneGeometry(barW, 1)
    const mMat = new THREE.MeshBasicMaterial({ color: 0x00d4ff, transparent: true, opacity: 0.3 })
    const mMesh = new THREE.Mesh(mGeo, mMat)
    mMesh.position.set(xPos, 0, -0.05)
    scene.add(mMesh)
    mirrorBars.push(mMesh)

    // 条顶发光点
    const dotGeo = new THREE.CircleGeometry(barW * 0.6, 8)
    const dotMat = new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0 })
    const dot = new THREE.Mesh(dotGeo, dotMat)
    dot.position.set(xPos, 0, 0.1)
    scene.add(dot)
    tipDots.push(dot)
  }

  animate()
}

function animate() {
  animFrameId = requestAnimationFrame(animate)
  if (!bars || !renderer) return
  const el = containerRef.value
  if (!el) return

  const halfH = el.clientHeight * 0.45
  const t = performance.now() / 1000
  const isActive = latestActive
  const rawLevel = latestAudioLevel

  // 平滑音量，快升慢降
  const lerpUp = 0.4
  const lerpDown = 0.08
  smoothLevel += (rawLevel - smoothLevel) * (rawLevel > smoothLevel ? lerpUp : lerpDown)

  const count = bars.length
  const center = count / 2

  // 背景辉光响应音量
  if (bgGlow) {
    const bgTarget = isActive ? 0.015 + smoothLevel * 0.12 : 0
    bgGlow.material.opacity += (bgTarget - bgGlow.material.opacity) * 0.1
    const bgC = lerpColor(spectrumColors, (Math.sin(t * 0.3) * 0.5 + 0.5))
    bgGlow.material.color.setRGB(bgC[0], bgC[1], bgC[2])
  }

  for (let i = 0; i < count; i++) {
    const dist = Math.abs(i - center) / center
    const envelope = 1 - dist * dist * 0.5
    const normalizedPos = i / count

    let target
    if (isActive) {
      // 环境波纹（极小幅度，仅当无声时可见）
      const w1 = Math.sin(t * 2.5 + i * 0.2) * 0.5 + 0.5
      const w2 = Math.sin(t * 4.1 + i * 0.35 + 1.2) * 0.5 + 0.5
      const ambient = (w1 * 0.5 + w2 * 0.5) * 0.04 * envelope

      // 音频驱动（主要贡献，大幅响应）
      const noise = 0.5 + Math.random() * 0.5
      const audioComp = smoothLevel * envelope * noise * 1.8

      target = ambient + 0.02 + audioComp
      target = Math.min(target, 1)
    } else {
      target = 0
    }

    currentLevels[i] += (target - currentLevels[i]) * 0.2
    const level = currentLevels[i]
    const h = Math.max(2, level * halfH)

    // 颜色：根据位置和音量从频谱色表取色
    const colorShift = smoothLevel * 0.4
    const colorPos = (normalizedPos + Math.sin(t * 0.5) * 0.1 + colorShift) % 1
    const [cr, cg, cb] = lerpColor(spectrumColors, colorPos)

    // 上方主条
    bars[i].scale.y = h
    bars[i].position.y = h / 2
    bars[i].material.color.setRGB(cr, cg, cb)
    bars[i].material.opacity = 0.75 + level * 0.25

    // 辉光
    glowBars[i].scale.y = h * 1.4
    glowBars[i].position.y = h / 2
    glowBars[i].material.opacity = level * 0.4
    glowBars[i].material.color.setRGB(cr, cg, cb)

    // 下方镜像
    const mh = h * 0.5
    mirrorBars[i].scale.y = mh
    mirrorBars[i].position.y = -mh / 2
    mirrorBars[i].material.color.setRGB(cr * 0.6, cg * 0.6, cb * 0.6)
    mirrorBars[i].material.opacity = level * 0.25

    // 条顶发光点
    tipDots[i].position.y = h
    tipDots[i].material.opacity = level > 0.1 ? Math.min(level * 1.8, 0.95) : 0
    tipDots[i].material.color.setRGB(
      Math.min(cr + 0.3, 1), Math.min(cg + 0.3, 1), Math.min(cb + 0.1, 1)
    )
  }

  renderer.render(scene, camera)
}

function handleResize() {
  const el = containerRef.value
  if (!el || !renderer || !camera) return
  const w = el.clientWidth
  const h = el.clientHeight
  camera.left = -w / 2
  camera.right = w / 2
  camera.top = h / 2
  camera.bottom = -h / 2
  camera.updateProjectionMatrix()
  renderer.setSize(w, h)
}

watch(() => props.audioLevel, (val) => { latestAudioLevel = val }, { immediate: true })
watch(() => props.active, (val) => {
  latestActive = val
  if (val) smoothLevel = 0
}, { immediate: true })

let resizeObserver = null

onMounted(() => {
  init()
  window.addEventListener('resize', handleResize)
  if (containerRef.value) {
    resizeObserver = new ResizeObserver(handleResize)
    resizeObserver.observe(containerRef.value)
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  if (resizeObserver) { resizeObserver.disconnect(); resizeObserver = null }
  if (animFrameId) cancelAnimationFrame(animFrameId)
  if (renderer) {
    renderer.dispose()
    renderer.forceContextLoss()
    const canvas = renderer.domElement
    if (canvas.parentNode) canvas.parentNode.removeChild(canvas)
    renderer = null
  }
  const disposeMeshes = (arr) => { if (arr) arr.forEach(b => { b.geometry.dispose(); b.material.dispose() }) }
  disposeMeshes(bars)
  disposeMeshes(glowBars)
  disposeMeshes(mirrorBars)
  disposeMeshes(tipDots)
  if (bgGlow) { bgGlow.geometry.dispose(); bgGlow.material.dispose() }
  scene = null
  camera = null
  bars = null
  glowBars = null
  mirrorBars = null
  tipDots = null
  bgGlow = null
})
</script>

<style lang="less" scoped>
.audio-visualizer {
  width: 100%;
  height: 100%;
  overflow: hidden;
  border-radius: 8px;
}
</style>
