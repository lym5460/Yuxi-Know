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
            ⚡ 大数据集渲染中，预计需要 3-5 秒
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
        <!-- 大数据集提示 -->
        <div v-if="graphData.nodes.length > 2000" class="performance-tip">
          <span class="tip-icon">⚡</span>
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
 * GraphCanvas - 3D 知识图谱可视化组件
 *
 * 融合 3d-force-graph 官方示例的功能：
 * - text-nodes: 使用 SpriteText 显示节点文本
 * - text-links: 使用 SpriteText 显示边文本
 * - click-to-focus: 点击节点相机聚焦
 * - highlight: 悬停高亮节点及邻居
 */
import ForceGraph3D from '3d-force-graph'
import SpriteText from 'three-spritetext'
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { useThemeStore } from '@/stores/theme'

const props = defineProps({
  /** 图谱数据，包含 nodes 和 edges 数组 */
  graphData: {
    type: Object,
    required: true,
    default: () => ({ nodes: [], edges: [] })
  },
  /** 图谱统计信息 */
  graphInfo: {
    type: Object,
    default: () => ({})
  },
  /** 节点标签字段名 */
  labelField: { type: String, default: 'name' },
  /** 搜索高亮关键词数组 */
  highlightKeywords: { type: Array, default: () => [] },
  /** 是否启用焦点邻居模式 */
  enableFocusNeighbor: { type: Boolean, default: true },
  /** 是否根据度数调整大小 */
  sizeByDegree: { type: Boolean, default: true }
})

const emit = defineEmits(['ready', 'data-rendered', 'node-click', 'edge-click', 'canvas-click'])

const container = ref(null)
const rootEl = ref(null)
const themeStore = useThemeStore()
const loading = ref(true)
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

// Highlight 状态（已禁用悬停高亮以提升性能）
// const highlightNodes = new Set()
// const highlightLinks = new Set()
// let hoverNode = null

/**
 * 获取 CSS 变量值
 */
function getCSSVariable(variableName, element = document.documentElement) {
  return getComputedStyle(element).getPropertyValue(variableName).trim()
}

/**
 * 检查 WebGL 支持
 */
function checkWebGLSupport() {
  try {
    const canvas = document.createElement('canvas')
    return !!canvas.getContext('webgl') || !!canvas.getContext('experimental-webgl')
  } catch (e) {
    return false
  }
}

/**
 * 检查节点是否匹配搜索关键词
 */
function shouldHighlightNode(node) {
  return props.highlightKeywords?.some(
    (kw) => kw.trim() !== '' && node.name.toLowerCase().includes(kw.toLowerCase())
  )
}

/**
 * 数据转换 + 建立邻居关系（参考 highlight 示例）
 */
function formatData() {
  const data = props.graphData || { nodes: [], edges: [] }

  // 计算节点度数
  const degrees = new Map()
  data.nodes.forEach((n) => degrees.set(String(n.id), 0))
  data.edges.forEach((e) => {
    const s = String(e.source_id)
    const t = String(e.target_id)
    degrees.set(s, (degrees.get(s) || 0) + 1)
    degrees.set(t, (degrees.get(t) || 0) + 1)
  })

  // 转换节点
  const nodes = (data.nodes || []).map((n) => {
    const degree = degrees.get(String(n.id)) || 0
    return {
      id: String(n.id),
      name: n[props.labelField] ?? n.name ?? String(n.id),
      group: n.type || 'default',
      degree: degree,
      val: props.sizeByDegree ? Math.max(1, degree * 0.3) : 1,
      neighbors: [], // 用于 highlight 功能
      links: [], // 用于 highlight 功能
      original: n
    }
  })

  // 转换边
  const links = (data.edges || []).map((e) => ({
    source: String(e.source_id),
    target: String(e.target_id),
    label: e.type ?? '',
    original: e
  }))

  // 建立节点邻居关系（参考 highlight 示例）
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

/**
 * 初始化图谱 - 融合 4 个示例的特性，支持自适应标签策略
 */
function initGraph() {
  if (!container.value || !webglSupported.value) return

  const width = container.value.offsetWidth
  const height = container.value.offsetHeight

  if (width === 0 || height === 0) {
    setTimeout(initGraph, 200)
    return
  }

  // 清理旧实例
  if (graphInstance) {
    try {
      graphInstance._destructor()
    } catch (e) {}
    graphInstance = null
  }
  container.value.innerHTML = ''

  const isDark = themeStore.isDark

  // 检测节点数量，决定是否显示 3D 文本标签
  const nodeCount = (props.graphData?.nodes || []).length
  const showNodeLabels = nodeCount <= 2000
  const showLinkLabels = nodeCount <= 2000

  console.log(`图谱节点数: ${nodeCount}, 显示节点标签: ${showNodeLabels}`)

  // 创建图谱实例
  graphInstance = ForceGraph3D()(container.value)
    .width(width)
    .height(height)
    .backgroundColor(getCSSVariable('--gray-0'))
    // 节点自动着色
    .nodeAutoColorBy('group')
    // 节点 tooltip（始终启用，参考 large-graph 示例）
    .nodeLabel((node) => node.name)

  // 1. text-nodes 示例：使用 SpriteText 显示节点文本（仅小数据集 ≤ 2000）
  if (showNodeLabels) {
    graphInstance
      .nodeThreeObject((node) => {
        const sprite = new SpriteText(node.name)
        sprite.material.depthWrite = false // 背景透明
        sprite.color = node.color || (isDark ? '#e0e0e0' : '#333333')
        sprite.textHeight = 8
        sprite.center.y = -0.6 // 将文本移到节点上方
        return sprite
      })
      .nodeThreeObjectExtend(true) // 保留原始节点球体
  }

  // 边样式
  graphInstance
    .linkWidth(1)
    .linkColor(() => getCSSVariable('--gray-400'))
    .linkOpacity(isDark ? 0.5 : 0.3)
    .linkDirectionalArrowLength(3)
    .linkDirectionalArrowRelPos(1)
    // 边 tooltip（始终启用）
    .linkLabel((link) => link.label || '')

  // 3. text-links 示例：使用 SpriteText 显示边文本（仅小数据集 ≤ 2000）
  if (showLinkLabels) {
    graphInstance
      .linkThreeObjectExtend(true)
      .linkThreeObject((link) => {
        if (!link.label) return null

        const sprite = new SpriteText(link.label)
        sprite.color = isDark ? '#888888' : 'lightgrey'
        sprite.textHeight = 3
        return sprite
      })
      .linkPositionUpdate((sprite, { start, end }) => {
        if (!sprite) return
        // 计算中点位置
        const middlePos = {
          x: start.x + (end.x - start.x) / 2,
          y: start.y + (end.y - start.y) / 2,
          z: start.z + (end.z - start.z) / 2
        }
        Object.assign(sprite.position, middlePos)
      })
  }

  graphInstance
    // 4. 悬停事件 - 用于自定义 tooltip（大数据集时）
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

    // 5. click-to-focus 示例：点击节点相机聚焦
    .onNodeClick((node) => {
      if (!node) return

      // 发送点击事件
      emit('node-click', {
        id: node.id,
        data: {
          label: node.name,
          degree: node.degree,
          original: node.original
        }
      })

      // 相机聚焦到节点（参考 click-to-focus 示例）
      const distance = 100
      const distRatio = 1 + distance / Math.hypot(node.x, node.y, node.z)

      const newPos =
        node.x || node.y || node.z
          ? { x: node.x * distRatio, y: node.y * distRatio, z: node.z * distRatio }
          : { x: 0, y: 0, z: distance }

      graphInstance.cameraPosition(
        newPos, // new position
        node, // lookAt ({ x, y, z })
        1000 // ms transition duration
      )
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

  // 扩展节点间距（参考 text-nodes/highlight 示例）
  graphInstance.d3Force('charge').strength(-120)

  emit('ready', graphInstance)
}

/**
 * 更新高亮显示（已禁用悬停高亮，仅保留搜索高亮）
 */
function updateHighlight() {
  if (!graphInstance) return
  // 悬停高亮已禁用
}

/**
 * 设置图谱数据
 */
function setGraphData() {
  if (!graphInstance) initGraph()
  if (!graphInstance) return

  // 显示加载状态
  loading.value = true
  loadingProgress.value = 0

  const data = formatData()

  console.log('开始设置图谱数据:', {
    nodes: data.nodes.length,
    links: data.links.length
  })

  // 模拟加载进度
  clearInterval(progressInterval)
  progressInterval = setInterval(() => {
    if (loadingProgress.value < 90) {
      loadingProgress.value += 10
    }
  }, 100)

  // 设置数据
  graphInstance.graphData(data)

  // 等待初始布局完成
  const waitTime = data.nodes.length > 2000 ? 3000 : data.nodes.length > 1000 ? 2000 : 1000
  setTimeout(() => {
    clearInterval(progressInterval)
    loadingProgress.value = 100

    setTimeout(() => {
      loading.value = false
      loadingProgress.value = 0
      applyHighlightKeywords()
      emit('data-rendered')
      console.log('图谱渲染完成')
    }, 300)
  }, waitTime)
}

/**
 * 应用搜索关键词高亮
 */
function applyHighlightKeywords() {
  if (!graphInstance) return

  const hasHighlightKeywords = props.highlightKeywords?.some((kw) => kw.trim() !== '')

  if (!hasHighlightKeywords) {
    // 恢复自动着色 - 直接使用 node.color（由 nodeAutoColorBy 自动设置）
    graphInstance.nodeColor((node) => node.color)
    return
  }

  // 搜索高亮 - 覆盖部分节点颜色
  graphInstance.nodeColor((node) => {
    if (shouldHighlightNode(node)) {
      return '#faad14' // 金黄色高亮
    }
    // 其他节点使用 nodeAutoColorBy 自动生成的颜色
    return node.color
  })
}

/**
 * 清除搜索高亮
 */
function clearHighlights() {
  if (!graphInstance) return
  // 恢复使用 nodeAutoColorBy 自动生成的颜色
  graphInstance.nodeColor((node) => node.color)
}

/**
 * 焦点模式 - 仅显示节点及邻居
 */
async function focusNode(id) {
  if (!graphInstance || !props.enableFocusNeighbor) return

  const data = graphInstance.graphData()
  const targetNode = data.nodes.find((n) => n.id === id)
  if (!targetNode) return

  const connectedNodeIds = new Set([id])

  // 使用节点的 neighbors 属性
  if (targetNode.neighbors) {
    targetNode.neighbors.forEach((neighbor) => connectedNodeIds.add(neighbor.id))
  }

  // 更新可见性
  graphInstance
    .nodeVisibility((node) => connectedNodeIds.has(node.id))
    .linkVisibility((link) => {
      const sourceId = link.source.id || link.source
      const targetId = link.target.id || link.target
      return connectedNodeIds.has(sourceId) && connectedNodeIds.has(targetId)
    })
}

/**
 * 清除焦点模式
 */
async function clearFocus() {
  if (!graphInstance) return
  graphInstance.nodeVisibility(true).linkVisibility(true)
}

/**
 * 刷新图谱
 */
function refreshGraph() {
  if (graphInstance) {
    try {
      graphInstance._destructor()
    } catch (e) {}
    graphInstance = null
  }
  if (container.value) container.value.innerHTML = ''

  // 清除高亮状态（已禁用）
  // highlightNodes.clear()
  // highlightLinks.clear()
  // hoverNode = null

  clearTimeout(renderTimeout)
  renderTimeout = setTimeout(() => {
    initGraph()
    setGraphData()
  }, 300)
}

/**
 * 适应视图
 */
function fitView() {
  if (graphInstance) {
    graphInstance.zoomToFit(1000, 50)
  }
}

/**
 * 居中视图
 */
function fitCenter() {
  if (graphInstance) {
    graphInstance.zoomToFit(500, 50)
  }
}

/**
 * 获取图谱实例
 */
function getInstance() {
  return graphInstance
}

// 监听数据变化
watch(
  () => props.graphData,
  () => {
    clearTimeout(renderTimeout)
    renderTimeout = setTimeout(() => setGraphData(), 50)
  },
  { deep: true }
)

// 监听关键词变化
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

// 监听主题切换
watch(
  () => themeStore.isDark,
  (isDark) => {
    if (graphInstance) {
      const nodeCount = graphInstance.graphData().nodes.length
      const showNodeLabels = nodeCount <= 2000
      const showLinkLabels = nodeCount <= 2000

      // 更新背景色
      graphInstance.backgroundColor(getCSSVariable('--gray-0'))

      // 更新边样式
      graphInstance.linkColor(() => getCSSVariable('--gray-400')).linkOpacity(isDark ? 0.5 : 0.3)

      // 仅在小数据集时更新 3D 文本标签颜色
      if (showNodeLabels) {
        graphInstance.nodeThreeObject((node) => {
          const sprite = new SpriteText(node.name)
          sprite.material.depthWrite = false
          sprite.color = node.color || (isDark ? '#e0e0e0' : '#333333')
          sprite.textHeight = 8
          sprite.center.y = -0.6
          return sprite
        })
      }

      if (showLinkLabels) {
        graphInstance.linkThreeObject((link) => {
          if (!link.label) return null
          const sprite = new SpriteText(link.label)
          sprite.color = isDark ? '#888888' : 'lightgrey'
          sprite.textHeight = 3
          return sprite
        })
      }
    }
  }
)

onMounted(() => {
  // 检查 WebGL 支持
  webglSupported.value = checkWebGLSupport()
  if (!webglSupported.value) {
    loading.value = false
    return
  }

  // ResizeObserver 监听容器尺寸
  if (window.ResizeObserver && container.value) {
    resizeObserver = new ResizeObserver(() => {
      if (!container.value || !graphInstance) return
      const width = container.value.offsetWidth
      const height = container.value.offsetHeight
      graphInstance.width(width).height(height)
    })
    resizeObserver.observe(container.value)
  }

  // 监听鼠标移动以更新 tooltip 位置
  const handleMouseMove = (e) => {
    if (tooltipVisible.value) {
      tooltipX.value = e.clientX + 10
      tooltipY.value = e.clientY + 10
    }
  }
  window.addEventListener('mousemove', handleMouseMove)

  // 初始化图谱
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

  // 清理状态（已禁用）
  // highlightNodes.clear()
  // highlightLinks.clear()
  // hoverNode = null
})

// 暴露公共方法
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
// 全局样式 - 确保 3d-force-graph 的 tooltip 可见
// 3d-force-graph 使用 scene-tooltip 类名
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
  overflow: visible; // 改为 visible，让 tooltip 可以显示在容器外
  background-color: var(--gray-0);
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
  background-color: var(--gray-0);
  backdrop-filter: blur(2px);
  z-index: 200; // 提高层级，确保在所有内容之上（包括空状态）

  .loading-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 32px;
    background: var(--gray-50);
    border-radius: 12px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
    border: 1px solid var(--gray-200);
  }

  .loading-tip {
    text-align: center;
    margin-top: 20px;

    .loading-text {
      font-size: 16px;
      color: var(--gray-900);
      font-weight: 600;
      margin-bottom: 8px;
    }

    .loading-subtext {
      font-size: 13px;
      color: var(--gray-600);
      margin-top: 6px;
      line-height: 1.6;

      &.warning {
        color: var(--color-warning-700);
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
  background: var(--gray-50);
  border: 1px solid var(--gray-300);
  border-radius: 4px;
  font-size: 14px;
  font-weight: 500;
  color: var(--gray-900);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
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
  z-index: 100; // 提高 z-index，但保持 pointer-events: none，不会挡住 tooltip

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
  background: var(--gray-50);
  border: 1px solid var(--gray-200);
  border-radius: 8px;
  padding: 12px 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  display: flex;
  gap: 20px;
  font-size: 14px;
  z-index: 101; // 比 slots 稍高，但不挡 tooltip

  .stat-item {
    display: flex;
    align-items: center;
    gap: 6px;

    .stat-label {
      color: var(--gray-600);
      font-weight: 500;
    }

    .stat-value {
      color: var(--primary-color);
      font-weight: 600;
      font-size: 16px;
    }

    .stat-total {
      color: var(--gray-500);
      font-size: 12px;
    }
  }

  .performance-tip {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 4px 10px;
    background: var(--color-warning-100);
    border-radius: 4px;
    border: 1px solid var(--color-warning-300);

    .tip-icon {
      font-size: 14px;
    }

    .tip-text {
      color: var(--color-warning-700);
      font-size: 12px;
      font-weight: 500;
    }
  }
}
</style>
