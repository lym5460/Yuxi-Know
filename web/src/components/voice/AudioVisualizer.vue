<template>
  <canvas ref="canvasRef" class="audio-visualizer" :width="width" :height="height"></canvas>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'

const props = defineProps({
  width: { type: Number, default: 200 },
  height: { type: Number, default: 60 },
  isActive: { type: Boolean, default: false },
  audioLevel: { type: Number, default: 0 },
  color: { type: String, default: null }
})

const canvasRef = ref(null)
let animationId = null
let bars = Array(12).fill(0)

function draw() {
  const canvas = canvasRef.value
  if (!canvas) return

  const ctx = canvas.getContext('2d')
  const barWidth = canvas.width / bars.length - 3
  const centerY = canvas.height / 2

  ctx.clearRect(0, 0, canvas.width, canvas.height)

  // 获取 CSS 变量颜色
  const computedColor =
    props.color ||
    getComputedStyle(document.documentElement).getPropertyValue('--main-color').trim() ||
    '#1890ff'

  bars.forEach((height, i) => {
    // 基于音频电平更新高度，添加随机变化
    const targetHeight = props.audioLevel * canvas.height * 0.8 * (0.5 + Math.random() * 0.5)
    bars[i] = bars[i] * 0.7 + targetHeight * 0.3

    const x = i * (barWidth + 3)
    const barHeight = Math.max(4, bars[i])
    const y = centerY - barHeight / 2

    ctx.fillStyle = computedColor
    ctx.beginPath()
    ctx.roundRect(x, y, barWidth, barHeight, 2)
    ctx.fill()
  })

  animationId = requestAnimationFrame(draw)
}

onMounted(() => {
  draw()
})

onUnmounted(() => {
  if (animationId) cancelAnimationFrame(animationId)
})
</script>

<style lang="less" scoped>
.audio-visualizer {
  border-radius: 4px;
}
</style>
