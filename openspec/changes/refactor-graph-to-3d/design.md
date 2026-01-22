# 设计：3D 力导向图架构

## 变更 ID
`refactor-graph-to-3d`

## 架构概述

本设计文档概述了将知识图谱可视化从 @antv/g6（2D canvas）迁移到 3d-force-graph（3D WebGL）的技术架构。

## 组件架构

### 当前架构（G6）
```
┌─────────────────────────────────────────┐
│         GraphView.vue                   │
│  （消费者 - 管理状态和操作）             │
└──────────────┬──────────────────────────┘
               │ props: graphData, events
               ▼
┌─────────────────────────────────────────┐
│       GraphCanvas.vue                   │
│  ┌───────────────────────────────────┐  │
│  │  @antv/g6 Graph 实例              │  │
│  │  - 2D canvas 渲染                 │  │
│  │  - d3-force 布局 (2D)             │  │
│  │  - 节点/边样式                    │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

### 目标架构（3d-force-graph）
```
┌─────────────────────────────────────────┐
│         GraphView.vue                   │
│  （消费者 - 无变更）                     │
└──────────────┬──────────────────────────┘
               │ 相同的 props 和 events
               ▼
┌─────────────────────────────────────────┐
│       GraphCanvas.vue（重构）            │
│  ┌───────────────────────────────────┐  │
│  │  3d-force-graph 实例              │  │
│  │  - ThreeJS/WebGL 渲染             │  │
│  │  - d3-force-3d 布局               │  │
│  │  - 3D 节点几何体                  │  │
│  │  - 相机控制                       │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │  数据转换层                       │  │
│  │  - G6 格式 → 3d-force-graph       │  │
│  │  - 度数计算                       │  │
│  │  - 从 CSS 变量映射颜色            │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

## 数据流

### 输入数据流
```
后端 API
    ↓
{ nodes: [...], edges: [...] }  ← 原始格式
    ↓
formatData()  ← 转换为 3d-force-graph 格式
    ↓
{
  nodes: [{ id, name, degree, val, color, ... }],
  links: [{ source, target, label, ... }]
}
    ↓
graph.graphData(data)  ← 在 3d-force-graph 实例上设置数据
    ↓
渲染的 3D 场景
```

### 事件流
```
用户交互（点击/悬停）
    ↓
3d-force-graph 事件处理器（onNodeClick, onLinkClick）
    ↓
从 3D 对象提取数据
    ↓
发出 Vue 事件（node-click, edge-click）
    ↓
父组件处理器（GraphView.vue）
    ↓
更新详情面板/焦点模式
```

## 关键设计决策

### 1. 渲染引擎：WebGL vs Canvas
**决定**：通过 3d-force-graph 使用 WebGL

**理由**：
- G6 使用 canvas 2D API，受 CPU 限制，无法扩展到 1000 个节点以上
- WebGL 将渲染卸载到 GPU，实现 10-100 倍的性能提升
- ThreeJS 在 WebGL 复杂性之上提供成熟的抽象
- 3d-force-graph 库处理 WebGL 设置和优化

**权衡**：
- ✅ 大型图的性能大幅提升
- ✅ 3D 可视化为密集图添加深度感知
- ⚠️ 更大的打包体积（~400kb ThreeJS）
- ⚠️ 3D 相机控制的学习曲线
- ❌ 不支持 IE11（2026 年可接受）

### 2. 力布局算法
**决定**：使用 d3-force-3d（d3-force 的 3D 版本）

**理由**：
- 当前实现通过 G6 的布局系统使用 d3-force（2D）
- d3-force-3d 是具有相同 API 的直接 3D 移植
- 相同的参数（电荷、链接距离、碰撞）直接转移
- 平滑迁移现有的布局调优

**配置**：
```javascript
graph
  .d3Force('charge', d3.forceManyBody().strength(-400))
  .d3Force('link', d3.forceLink().distance(100).strength(0.8))
  .d3Force('center', d3.forceCenter())
  .d3Force('collide', d3.forceCollide(40).strength(0.8))
  .d3AlphaDecay(0.1)
  .d3VelocityDecay(0.6)
```

### 3. 节点表示
**决定**：使用动态大小的球体几何

**实现**：
```javascript
graph
  .nodeThreeObject(node => {
    const geometry = new THREE.SphereGeometry(getNodeSize(node), 16, 16)
    const material = new THREE.MeshLambertMaterial({
      color: getNodeColor(node),
      transparent: true,
      opacity: 0.9
    })
    return new THREE.Mesh(geometry, material)
  })
```

**考虑的替代方案**：
- **选项 A**：简单的彩色球体 → **已选择**（干净、性能好）
- 选项 B：基于 Sprite 的 2D 圆圈 → 3D 感觉较弱
- 选项 C：复杂几何体（立方体、图标）→ 性能损失

### 4. 标签渲染
**决定**：使用 CSS2DRenderer 渲染 HTML 标签

**理由**：
- 3d-force-graph 支持 `.nodeLabel()` 访问器用于文本标签
- 使用 sprites 的内置标签渲染（性能好）
- 如需要，可降级到 CSS2DRenderer 用于丰富的 HTML 标签

**实现**：
```javascript
graph
  .nodeLabel(node => node.name)
  .nodeAutoColorBy('label')
  .linkLabel(link => link.label || '')
  .linkWidth(1.2)
  .linkDirectionalArrowLength(3.5)
  .linkDirectionalArrowRelPos(1)
```

### 5. 主题集成
**决定**：从 CSS 变量动态提取颜色

**当前方法**（保留）：
```javascript
function getCSSVariable(name) {
  return getComputedStyle(document.documentElement)
    .getPropertyValue(name).trim()
}

const nodeColor = getCSSVariable('--gray-700')
const edgeColor = getCSSVariable('--gray-400')
```

**监听主题变化**：
```javascript
watch(() => themeStore.isDark, () => {
  if (graphInstance) {
    // 更新节点和连接颜色而无需完全重新渲染
    graphInstance
      .nodeColor(node => getNodeColorDynamic(node))
      .linkColor(getCSSVariable('--gray-400'))
  }
})
```

### 6. 交互模式

#### 节点点击
```javascript
graph.onNodeClick(node => {
  emit('node-click', {
    id: node.id,
    data: {
      label: node.name,
      degree: node.degree,
      original: node.original
    }
  })
})
```

#### 焦点模式（显示节点 + 邻居）
```javascript
function focusNode(nodeId) {
  const connectedNodeIds = new Set([nodeId])
  const connectedLinkIds = new Set()

  // 通过连接查找邻居
  graphData.links.forEach(link => {
    if (link.source.id === nodeId || link.source === nodeId) {
      connectedNodeIds.add(link.target.id || link.target)
      connectedLinkIds.add(link)
    }
    if (link.target.id === nodeId || link.target === nodeId) {
      connectedNodeIds.add(link.source.id || link.source)
      connectedLinkIds.add(link)
    }
  })

  // 更新可见性
  graph
    .nodeVisibility(node => connectedNodeIds.has(node.id))
    .linkVisibility(link => connectedLinkIds.has(link))
}
```

#### 关键词高亮
```javascript
function applyHighlightKeywords(keywords) {
  graph.nodeColor(node => {
    const isHighlighted = keywords.some(kw =>
      node.name.toLowerCase().includes(kw.toLowerCase())
    )
    return isHighlighted
      ? '#ff0000'  // 高亮颜色
      : getDefaultNodeColor(node)
  })
}
```

### 7. 相机控制
**决定**：使用内置的轨迹球控制

**配置**：
```javascript
graph
  .enableNodeDrag(true)
  .enableNavigationControls(true)
  .showNavInfo(false)  // 隐藏 FPS 计数器
```

**适应视图实现**：
```javascript
function fitView() {
  const distance = 300
  graph.cameraPosition(
    { x: 0, y: 0, z: distance }, // 新位置
    { x: 0, y: 0, z: 0 },        // 看向中心
    1000                          // 过渡持续时间（毫秒）
  )
}
```

### 8. 性能优化

#### 延迟渲染
- 使用 `warmupTicks: 0` 防止初始模拟延迟
- 在渲染前在后台运行布局模拟
- 在初始化期间显示加载状态

#### 细节层次（LOD）
```javascript
// 缩小时隐藏标签
graph.nodeLabel(node => {
  const cameraDistance = graph.cameraDistance()
  return cameraDistance < 500 ? node.name : ''
})
```

#### 节流更新
```javascript
// 防抖快速数据更新
let updateTimeout
function setGraphData(newData) {
  clearTimeout(updateTimeout)
  updateTimeout = setTimeout(() => {
    graph.graphData(formatData(newData))
  }, 100)
}
```

## 组件接口（不变）

### Props
```typescript
interface GraphCanvasProps {
  graphData: {
    nodes: Array<{ id: string, [key: string]: any }>
    edges: Array<{ source_id: string, target_id: string, [key: string]: any }>
  }
  graphInfo?: {
    node_count?: number
    edge_count?: number
  }
  labelField?: string
  autoFit?: boolean
  autoResize?: boolean
  layoutOptions?: object
  nodeStyleOptions?: object
  edgeStyleOptions?: object
  enableFocusNeighbor?: boolean
  sizeByDegree?: boolean
  highlightKeywords?: string[]
}
```

### 事件
```typescript
interface GraphCanvasEvents {
  'ready': (graphInstance: any) => void
  'data-rendered': () => void
  'node-click': (nodeData: any) => void
  'edge-click': (edgeData: any) => void
  'canvas-click': () => void
}
```

### 暴露的方法
```typescript
interface GraphCanvasMethods {
  refreshGraph: () => void
  fitView: () => void
  fitCenter: () => void
  getInstance: () => any
  focusNode: (id: string) => void
  clearFocus: () => void
  setData: (data: any) => void
  applyHighlightKeywords: () => void
  clearHighlights: () => void
}
```

## 迁移安全性

### 向后兼容性
- **消费者组件**：无需更改（GraphView.vue 等）
- **数据格式**：后端 API 不变
- **事件**：相同的事件名称和有效载荷结构
- **样式**：使用 base.css 中的相同 CSS 变量

### 测试策略
1. **单元测试**：数据转换函数
2. **集成测试**：组件 prop/事件契约
3. **视觉回归**：图状态的截图比较
4. **性能测试**：500/1000/2000 节点图的渲染时间
5. **手动测试**：每个消费者组件（GraphView、KnowledgeGraphSection 等）

### 回滚计划
如果出现关键问题：
1. 通过从 git 历史恢复 GraphCanvas.vue 回退到 G6
2. 降级 package.json 依赖
3. 性能问题是迁移驱动因素，因此回滚不太可能

## 打包大小分析

### 当前（G6）
- @antv/g6: ~200kb（压缩后）
- 图相关 JS 总计: ~200kb

### 目标（3d-force-graph）
- 3d-force-graph: ~50kb
- three: ~400kb（压缩后）
- d3-force-3d: ~20kb
- 图相关 JS 总计: ~470kb

**缓解措施**：
- ThreeJS 支持 tree-shaking（仅包含需要的模块）
- 延迟加载图组件（路由级代码分割）
- **预估最终**：~350kb（比当前 +150kb）

### 可接受因为：
- 性能提升证明了打包体积增加的合理性
- 仅在图可视化路由上加载
- 使用 HTTP/2 缓存的一次性下载

## 未来增强（不在范围内）

这些是潜在的改进，不包括在此变更中：

1. **VR/AR 支持**：ThreeJS 支持 WebXR 集成
2. **粒子效果**：连接上的动画粒子用于流可视化
3. **分层 DAG 模式**：3d-force-graph 支持用于树布局的 `dagMode`
4. **图聚类**：将节点分组到 3D 集群/区域
5. **时间序列动画**：动画化图的演变
6. **导出为 3D 格式**：将场景导出为 GLB/GLTF 供外部查看器使用

## 结论

此设计为迁移到 3d-force-graph 提供了坚实的基础，同时保持与现有消费者的完全向后兼容性。基于 WebGL 的渲染将解锁 4000+ 节点图的流畅可视化，直接解决了促使此重构的性能瓶颈。
