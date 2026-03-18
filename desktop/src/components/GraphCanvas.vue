<template>
  <div class="graph-canvas-container" ref="rootEl">
    <!-- WebGL 不支持警告 -->
    <div v-if="!webglSupported" class="webgl-error">
      <a-alert type="warning" message="您的浏览器不支持 WebGL，无法渲染 3D 图谱" show-icon />
    </div>
    <!-- 加载状态 -->
    <div v-if="loading && webglSupported" class="loading-overlay">
      <div class="loading-content">
        <a-spin size="large" />
        <div class="loading-tip">
          <div class="loading-text">正在渲染图谱... {{ loadingProgress }}%</div>
          <div class="loading-subtext" v-if="graphData.nodes.length > 0">
            {{ graphData.nodes.length }} 个节点，{{ graphData.edges.length }} 条边
          </div>
          <div class="loading-subtext warning" v-if="graphData.nodes.length > 2000">
            大数据集渲染中，预计需要 3-5 秒
          </div>
        </div>
      </div>
    </div>
    <!-- 自定义 Tooltip -->
    <div
      v-if="tooltipVisible"
      class="custom-tooltip"
      :style="{ left: tooltipX + 'px', top: tooltipY + 'px' }"
    >
      {{ tooltipContent }}
    </div>
    <div class="graph-canvas" ref="container"></div>
    <div class="slots">
      <div v-if="$slots.top" class="overlay top">
        <slot name="top" />
      </div>
      <div class="canvas-content">
        <slot name="content" />
      </div>
      <!-- Statistical Info Panel -->
      <div class="graph-stats-panel" v-if="graphData.nodes.length > 0">
        <div class="stat-item">
          <span class="stat-label">节点</span>
          <span class="stat-value">{{ graphData.nodes.length }}</span>
          <span v-if="graphInfo?.node_count" class="stat-total">/ {{ graphInfo.node_count }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">边</span>
          <span class="stat-value">{{ graphData.edges.length }}</span>
          <span v-if="graphInfo?.edge_count" class="stat-total">/ {{ graphInfo.edge_count }}</span>
        </div>
        <div v-if="graphData.nodes.length > 2000" class="performance-tip">
          <span class="tip-text">性能模式</span>
        </div>
      </div>
      <div v-if="$slots.bottom" class="overlay bottom">
        <slot name="bottom" />
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * GraphCanvas - 3D 知识图谱可视化组件 (桌面端适配版)
 *
 * 基于 3d-force-graph，支持：
 * - text-nodes: 使用 SpriteText 显示节点文本
 * - text-links: 使用 SpriteText 显示边文本
 * - click-to-focus: 点击节点相机聚焦
 */
import ForceGraph3D from '3d-force-graph'
import SpriteText from 'three-spritetext'
import { onMounted, onUnmounted, ref, watch } from 'vue'

const props = defineProps({
  graphData: {
    type: Object,
    required: true,
    default: () => ({ nodes: [], edges: [] })
  },
  graphInfo: {
    type: Object,
    default: () => ({})
  },
  labelField: { type: String, default: 'name' },
  highlightKeywords: { type: Array, default: () => [] },
  enableFocusNeighbor: { type: Boolean, default: true },
  sizeByDegree: { type: Boolean, default: true }
})

const emit = defineEmits(['ready', 'data-rendered', 'node-click', 'edge-click', 'canvas-click'])

const container = ref(null)
const rootEl = ref(null)
const loading = ref(false)
const loadingProgress = ref(0)
const webglSupported = ref(true)
const tooltipContent = ref('')
const tooltipVisible = ref(false)
const tooltipX = ref(0)
const tooltipY = ref(0)
let graphInstance = null
let resizeObserver = null
let renderTimeout = null
let progressInterval = null

// 桌面端始终暗色主题
const BG_COLOR = '#0a0e17'
const NODE_TEXT_COLOR = '#e0e0e0'
const LINK_COLOR = 'rgba(255,255,255,0.2)'
const LINK_LABEL_COLOR = '#888888'

function checkWebGLSupport() {
  try {
    const canvas = document.createElement('canvas')
    return !!canvas.getContext('webgl') || !!canvas.getContext('experimental-webgl')
  } catch (e) {
    return false
  }
}

function shouldHighlightNode(node) {
  return props.highlightKeywords?.some(
    (kw) => kw.trim() !== '' && node.name.toLowerCase().includes(kw.toLowerCase())
  )
}

function formatData() {
  const data = props.graphData || { nodes: [], edges: [] }

  const degrees = new Map()
  data.nodes.forEach((n) => degrees.set(String(n.id), 0))
  data.edges.forEach((e) => {
    const s = String(e.source_id)
    const t = String(e.target_id)
    degrees.set(s, (degrees.get(s) || 0) + 1)
    degrees.set(t, (degrees.get(t) || 0) + 1)
  })

  const nodes = (data.nodes || []).map((n) => {
    const degree = degrees.get(String(n.id)) || 0
    return {
      id: String(n.id),
      name: n[props.labelField] ?? n.name ?? String(n.id),
      group: n.type || 'default',
      degree: degree,
      val: props.sizeByDegree ? Math.max(1, degree * 0.3) : 1,
      neighbors: [],
      links: [],
      original: n
    }
  })

  const links = (data.edges || []).map((e) => ({
    source: String(e.source_id),
    target: String(e.target_id),
    label: e.type ?? '',
    original: e
  }))

  const nodeMap = new Map(nodes.map((n) => [n.id, n]))
  links.forEach((link) => {
    const a = nodeMap.get(link.source)
    const b = nodeMap.get(link.target)
    if (a && b) {
      a.neighbors.push(b)
      b.neighbors.push(a)
      a.links.push(link)
      b.links.push(link)
    }
  })

  return { nodes, links }
}

function initGraph() {
  if (!container.value || !webglSupported.value) return

  const width = container.value.offsetWidth
  const height = container.value.offsetHeight

  if (width === 0 || height === 0) {
    setTimeout(initGraph, 200)
    return
  }

  if (graphInstance) {
    try {
      graphInstance._destructor()
    } catch (e) {}
    graphInstance = null
  }
  container.value.innerHTML = ''

  const nodeCount = (props.graphData?.nodes || []).length
  const showNodeLabels = nodeCount <= 2000
  const showLinkLabels = nodeCount <= 2000

  graphInstance = ForceGraph3D()(container.value)
    .width(width)
    .height(height)
    .backgroundColor(BG_COLOR)
    .nodeAutoColorBy('group')
    .nodeLabel('')

  if (showNodeLabels) {
    graphInstance
      .nodeThreeObject((node) => {
        const sprite = new SpriteText(node.name)
        sprite.material.depthWrite = false
        sprite.color = node.color || NODE_TEXT_COLOR
        sprite.textHeight = 8
        sprite.center.y = -0.6
        return sprite
      })
      .nodeThreeObjectExtend(true)
  }

  graphInstance
    .linkWidth(1)
    .linkColor(() => LINK_COLOR)
    .linkOpacity(0.5)
    .linkDirectionalArrowLength(3)
    .linkDirectionalArrowRelPos(1)
    .linkLabel('')

  if (showLinkLabels) {
    graphInstance
      .linkThreeObjectExtend(true)
      .linkThreeObject((link) => {
        if (!link.label) return null
        const sprite = new SpriteText(link.label)
        sprite.color = LINK_LABEL_COLOR
        sprite.textHeight = 3
        return sprite
      })
      .linkPositionUpdate((sprite, { start, end }) => {
        if (!sprite) return
        const middlePos = {
          x: start.x + (end.x - start.x) / 2,
          y: start.y + (end.y - start.y) / 2,
          z: start.z + (end.z - start.z) / 2
        }
        Object.assign(sprite.position, middlePos)
      })
  }

  graphInstance
    .onNodeHover((node) => {
      if (node) {
        tooltipContent.value = node.name
        tooltipVisible.value = true
      } else {
        tooltipVisible.value = false
      }
    })
    .onLinkHover((link) => {
      if (link && link.label) {
        tooltipContent.value = link.label
        tooltipVisible.value = true
      } else if (!link) {
        tooltipVisible.value = false
      }
    })
    .onNodeClick((node) => {
      if (!node) return

      emit('node-click', {
        id: node.id,
        data: {
          label: node.name,
          degree: node.degree,
          original: node.original
        }
      })

      const distance = 100
      const distRatio = 1 + distance / Math.hypot(node.x, node.y, node.z)
      const newPos =
        node.x || node.y || node.z
          ? { x: node.x * distRatio, y: node.y * distRatio, z: node.z * distRatio }
          : { x: 0, y: 0, z: distance }

      graphInstance.cameraPosition(newPos, node, 1000)
    })
    .onLinkClick((link) => {
      if (!link) return
      emit('edge-click', {
        id: link.original?.id,
        source: link.source.id || link.source,
        target: link.target.id || link.target,
        data: {
          label: link.label,
          original: link.original
        }
      })
    })
    .onBackgroundClick(() => {
      emit('canvas-click')
    })

  graphInstance.d3Force('charge').strength(-120)
  emit('ready', graphInstance)
}

function setGraphData() {
  if (!graphInstance) initGraph()
  if (!graphInstance) return

  const data = formatData()

  // 无数据时直接跳过加载动画
  if (data.nodes.length === 0) {
    loading.value = false
    graphInstance.graphData(data)
    return
  }

  loading.value = true
  loadingProgress.value = 0

  clearInterval(progressInterval)
  progressInterval = setInterval(() => {
    if (loadingProgress.value < 90) {
      loadingProgress.value += 10
    }
  }, 100)

  graphInstance.graphData(data)

  const waitTime = data.nodes.length > 2000 ? 3000 : data.nodes.length > 1000 ? 2000 : 1000
  setTimeout(() => {
    clearInterval(progressInterval)
    loadingProgress.value = 100

    setTimeout(() => {
      loading.value = false
      loadingProgress.value = 0
      applyHighlightKeywords()
      emit('data-rendered')
    }, 300)
  }, waitTime)
}

function applyHighlightKeywords() {
  if (!graphInstance) return

  const hasHighlightKeywords = props.highlightKeywords?.some((kw) => kw.trim() !== '')

  if (!hasHighlightKeywords) {
    graphInstance.nodeColor((node) => node.color)
    return
  }

  graphInstance.nodeColor((node) => {
    if (shouldHighlightNode(node)) {
      return '#faad14'
    }
    return node.color
  })
}

function clearHighlights() {
  if (!graphInstance) return
  graphInstance.nodeColor((node) => node.color)
}

async function focusNode(id) {
  if (!graphInstance || !props.enableFocusNeighbor) return

  const data = graphInstance.graphData()
  const targetNode = data.nodes.find((n) => n.id === id)
  if (!targetNode) return

  const connectedNodeIds = new Set([id])
  if (targetNode.neighbors) {
    targetNode.neighbors.forEach((neighbor) => connectedNodeIds.add(neighbor.id))
  }

  graphInstance
    .nodeVisibility((node) => connectedNodeIds.has(node.id))
    .linkVisibility((link) => {
      const sourceId = link.source.id || link.source
      const targetId = link.target.id || link.target
      return connectedNodeIds.has(sourceId) && connectedNodeIds.has(targetId)
    })
}

async function clearFocus() {
  if (!graphInstance) return
  graphInstance.nodeVisibility(true).linkVisibility(true)
}

function refreshGraph() {
  if (graphInstance) {
    try {
      graphInstance._destructor()
    } catch (e) {}
    graphInstance = null
  }
  if (container.value) container.value.innerHTML = ''

  clearTimeout(renderTimeout)
  renderTimeout = setTimeout(() => {
    initGraph()
    setGraphData()
  }, 300)
}

function fitView() {
  if (graphInstance) {
    graphInstance.zoomToFit(1000, 50)
  }
}

function fitCenter() {
  if (graphInstance) {
    graphInstance.zoomToFit(500, 50)
  }
}

function getInstance() {
  return graphInstance
}

watch(
  () => props.graphData,
  () => {
    clearTimeout(renderTimeout)
    renderTimeout = setTimeout(() => setGraphData(), 50)
  },
  { deep: true }
)

watch(
  () => props.highlightKeywords,
  () => {
    if (graphInstance) {
      clearHighlights()
      setTimeout(() => applyHighlightKeywords(), 50)
    }
  },
  { deep: true }
)

onMounted(() => {
  webglSupported.value = checkWebGLSupport()
  if (!webglSupported.value) {
    loading.value = false
    return
  }

  if (window.ResizeObserver && container.value) {
    resizeObserver = new ResizeObserver(() => {
      if (!container.value || !graphInstance) return
      const width = container.value.offsetWidth
      const height = container.value.offsetHeight
      graphInstance.width(width).height(height)
    })
    resizeObserver.observe(container.value)
  }

  const handleMouseMove = (e) => {
    if (tooltipVisible.value) {
      tooltipX.value = e.clientX + 10
      tooltipY.value = e.clientY + 10
    }
  }
  window.addEventListener('mousemove', handleMouseMove)

  clearTimeout(renderTimeout)
  renderTimeout = setTimeout(() => {
    initGraph()
    setGraphData()
  }, 300)
})

onUnmounted(() => {
  if (resizeObserver && container.value) {
    resizeObserver.unobserve(container.value)
  }
  clearTimeout(renderTimeout)
  clearInterval(progressInterval)
  try {
    graphInstance?._destructor()
  } catch (e) {}
  graphInstance = null
})

defineExpose({
  refreshGraph,
  fitView,
  fitCenter,
  getInstance,
  focusNode,
  clearFocus,
  setData: setGraphData,
  applyHighlightKeywords,
  clearHighlights
})
</script>

<style lang="less">
:global(.scene-tooltip) {
  pointer-events: none !important;
  z-index: 99999 !important;
  position: fixed !important;
}
</style>

<style lang="less" scoped>
.graph-canvas-container {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: visible;
  background-color: #0a0e17;
}

.webgl-error {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 10;
  width: 80%;
  max-width: 500px;
}

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: rgba(10, 14, 23, 0.9);
  backdrop-filter: blur(2px);
  z-index: 200;

  .loading-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 32px;
    background: #141a26;
    border-radius: 12px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
    border: 1px solid #1e2a3a;
  }

  .loading-tip {
    text-align: center;
    margin-top: 20px;

    .loading-text {
      font-size: 16px;
      color: #e4eaf2;
      font-weight: 600;
      margin-bottom: 8px;
    }

    .loading-subtext {
      font-size: 13px;
      color: #8899aa;
      margin-top: 6px;
      line-height: 1.6;

      &.warning {
        color: #faad14;
        font-weight: 500;
      }
    }
  }
}

.graph-canvas {
  width: 100%;
  height: 100%;
}

.custom-tooltip {
  position: fixed;
  padding: 6px 10px;
  background: #1e2a3a;
  border: 1px solid #2a3a4e;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 500;
  color: #e4eaf2;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  pointer-events: none;
  z-index: 99999;
  white-space: nowrap;
  max-width: 300px;
  word-break: break-all;
}

.slots {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
  z-index: 100;

  > * {
    pointer-events: auto;
  }
}

.overlay {
  position: absolute;
  left: 0;
  right: 0;
  padding: 20px;

  &.top {
    top: 0;
  }

  &.bottom {
    bottom: 0;
  }
}

.canvas-content {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  pointer-events: none;
}

.graph-stats-panel {
  position: absolute;
  bottom: 20px;
  right: 20px;
  background: #141a26;
  border: 1px solid #1e2a3a;
  border-radius: 8px;
  padding: 12px 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  display: flex;
  gap: 20px;
  font-size: 14px;
  z-index: 101;

  .stat-item {
    display: flex;
    align-items: center;
    gap: 6px;

    .stat-label {
      color: #8899aa;
      font-weight: 500;
    }

    .stat-value {
      color: #00d4ff;
      font-weight: 600;
      font-size: 16px;
    }

    .stat-total {
      color: #667788;
      font-size: 12px;
    }
  }

  .performance-tip {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 4px 10px;
    background: rgba(250, 173, 20, 0.1);
    border-radius: 4px;
    border: 1px solid rgba(250, 173, 20, 0.3);

    .tip-text {
      color: #faad14;
      font-size: 12px;
      font-weight: 500;
    }
  }
}
</style>
