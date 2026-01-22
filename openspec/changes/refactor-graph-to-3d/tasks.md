# 任务清单：知识图谱重构为 3D

## 变更 ID
`refactor-graph-to-3d`

## 概述
此任务清单将从 @antv/g6 迁移到 3d-force-graph 的工作分解为小型、可验证的工作项。每个任务都能交付用户可见的进展，并包含验证步骤。

## 任务序列

### 阶段 1：基础与设置
**目标**：安装依赖并设置基本的 3D 渲染

#### 任务 1.1：更新包依赖
**描述**：添加 3d-force-graph 和 three.js，移除 @antv/g6

**步骤**：
1. 编辑 `web/package.json`：
   - 移除：`"@antv/g6": "^5.0.49"`
   - 添加：`"3d-force-graph": "^1.73.5"`
   - 添加：`"three": "^0.160.0"`
2. 运行 `docker compose exec web-dev pnpm install` 安装新依赖
3. 验证控制台中没有损坏的导入

**验证**：
- [x] `pnpm install` 成功完成，无错误
- [x] 控制台无关于缺少 G6 模块的错误（初期预期）
- [x] `node_modules/3d-force-graph` 存在

**完成时间**：已完成
**预计耗时**：10 分钟

---

#### 任务 1.2：创建基本的 3d-force-graph 脚手架
**描述**：用最小的 3d-force-graph 设置替换 G6 初始化

**步骤**：
1. 备份当前的 `GraphCanvas.vue` 为 `GraphCanvas.vue.backup`
2. 替换 G6 导入为：`import ForceGraph3D from '3d-force-graph'`
3. 将 `new Graph()` 替换为 `ForceGraph3D(container.value)`
4. 设置最小图数据：`graph.graphData({ nodes: [], links: [] })`
5. 移除所有 G6 特定配置（布局、行为等）

**验证**：
- [x] 组件编译无错误
- [x] GraphView 页面渲染空的 3D 画布
- [x] 无控制台错误

**完成时间**：已完成
**预计耗时**：20 分钟

---

#### 任务 1.3：实现数据转换层
**描述**：将 G6 格式 `{nodes, edges}` 转换为 3d-force-graph 格式 `{nodes, links}`

**步骤**：
1. 修改 `formatData()` 函数：
   ```javascript
   function formatData() {
     const data = props.graphData || { nodes: [], edges: [] }

     // 计算度数
     const degrees = new Map()
     data.nodes.forEach(n => degrees.set(String(n.id), 0))
     data.edges.forEach(e => {
       const s = String(e.source_id)
       const t = String(e.target_id)
       degrees.set(s, (degrees.get(s) || 0) + 1)
       degrees.set(t, (degrees.get(t) || 0) + 1)
     })

     // 转换节点
     const nodes = data.nodes.map(n => ({
       id: String(n.id),
       name: n[props.labelField] ?? n.name ?? String(n.id),
       degree: degrees.get(String(n.id)) || 0,
       val: props.sizeByDegree ? Math.min(15 + (degrees.get(String(n.id)) || 0) * 5, 50) : 24,
       original: n
     }))

     // 转换边为连接
     const links = data.edges.map((e, idx) => ({
       source: String(e.source_id),
       target: String(e.target_id),
       label: e.type ?? '',
       original: e
     }))

     return { nodes, links }
   }
   ```
2. 更新 `setGraphData()` 使用新格式：
   ```javascript
   const data = formatData()
   graphInstance.graphData(data)
   ```

**验证**：
- [x] 示例图数据（100 个节点）在 3D 中渲染
- [x] 节点数量与输入数据匹配
- [x] 连接正确连接源/目标节点

**完成时间**：已完成
**预计耗时**：30 分钟

---

### 阶段 2：视觉样式
**目标**：用 3D 等效版本匹配 G6 的视觉外观

#### 任务 2.1：实现节点样式
**描述**：为节点应用颜色、大小和标签

**步骤**：
1. 添加节点大小访问器：
   ```javascript
   graph.nodeVal(node => node.val)
   ```
2. 从 CSS 变量添加节点颜色：
   ```javascript
   graph.nodeColor(node => getCSSVariable('--gray-700'))
   ```
3. 添加节点标签：
   ```javascript
   graph.nodeLabel(node => node.name)
   ```
4. 配置节点材质：
   ```javascript
   graph
     .nodeOpacity(0.9)
     .nodeResolution(16)  // 球体细节
   ```

**验证**：
- [x] 节点显示基于度数的正确大小
- [x] 节点颜色匹配主题（检查明暗模式）
- [x] 节点标签在悬停时或始终可见

**完成时间**：已完成
**预计耗时**：30 分钟

---

#### 任务 2.2：实现连接（边）样式
**描述**：为节点之间的连接添加箭头和标签样式

**步骤**：
1. 配置连接外观：
   ```javascript
   graph
     .linkColor(() => getCSSVariable('--gray-400'))
     .linkWidth(1.2)
     .linkOpacity(0.8)
     .linkDirectionalArrowLength(3.5)
     .linkDirectionalArrowRelPos(1)
     .linkCurvature(0.1)  // 重叠边的轻微曲线
   ```
2. 添加连接标签：
   ```javascript
   graph.linkLabel(link => link.label || '')
   ```

**验证**：
- [x] 节点之间渲染连接
- [x] 定向箭头出现在目标节点处
- [x] 连接标签在悬停时或始终可见
- [x] 连接颜色匹配主题

**完成时间**：已完成
**预计耗时**：20 分钟

---

#### 任务 2.3：配置力布局参数
**描述**：调整物理模拟以匹配 G6 布局行为

**步骤**：
1. 设置力：
   ```javascript
   graph
     .d3Force('charge', d3.forceManyBody().strength(-400).distanceMax(600))
     .d3Force('link', d3.forceLink().distance(100).strength(0.8))
     .d3Force('center', d3.forceCenter())
     .d3Force('collide', d3.forceCollide(40).strength(0.8))
     .d3AlphaDecay(0.1)
     .d3VelocityDecay(0.6)
     .warmupTicks(100)  // 渲染前预模拟
     .cooldownTicks(150)
   ```
2. 如需要，导入 d3-force-3d：`import * as d3 from 'd3'`

**验证**：
- [x] 节点均匀分布，无聚集
- [x] 无重叠节点（碰撞检测工作）
- [x] 布局在 3 秒内稳定
- [x] 视觉外观类似 G6 布局

**完成时间**：已完成
**预计耗时**：30 分钟

---

### 阶段 3：交互
**目标**：恢复所有用户交互（点击、拖拽、缩放）

#### 任务 3.1：实现节点点击事件
**描述**：用户点击节点时发出 `node-click` 事件

**步骤**：
1. 添加点击处理器：
   ```javascript
   graph.onNodeClick(node => {
     if (!node) return
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
2. 确保事件有效载荷匹配 G6 格式

**验证**：
- [x] 点击节点打开详情面板
- [x] 详情面板显示正确的节点数据
- [x] 多次点击正常工作

**完成时间**：已完成
**预计耗时**：15 分钟

---

#### 任务 3.2：实现连接点击事件
**描述**：用户点击连接时发出 `edge-click` 事件

**步骤**：
1. 添加连接点击处理器：
   ```javascript
   graph.onLinkClick(link => {
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
   ```

**验证**：
- [x] 点击连接打开边详情面板
- [x] 边数据（源、目标、类型）正确显示

**完成时间**：已完成
**预计耗时**：15 分钟

---

#### 任务 3.3：实现画布点击事件
**描述**：用户点击空白处时发出 `canvas-click`

**步骤**：
1. 添加背景点击处理器：
   ```javascript
   graph.onBackgroundClick(() => {
     emit('canvas-click')
   })
   ```
2. 测试背景点击时关闭详情面板

**验证**：
- [x] 点击空的 3D 空间关闭详情面板
- [x] 与节点/连接点击无冲突

**完成时间**：已完成
**预计耗时**：10 分钟

---

#### 任务 3.4：启用相机控制
**描述**：配置缩放、旋转、平移控制

**步骤**：
1. 启用内置控制：
   ```javascript
   graph
     .enableNodeDrag(true)
     .enableNavigationControls(true)
     .showNavInfo(false)  // 隐藏 FPS 覆盖层
   ```
2. 设置初始相机位置：
   ```javascript
   graph.cameraPosition({ x: 0, y: 0, z: 300 })
   ```

**验证**：
- [x] 鼠标拖拽旋转相机
- [x] 鼠标滚轮缩放
- [x] 右键拖拽平移视图
- [x] 拖拽节点在 3D 空间中移动它们

**完成时间**：已完成
**预计耗时**：10 分钟

---

### 阶段 4：高级功能
**目标**：实现高亮、焦点和适应视图功能

#### 任务 4.1：实现关键词高亮
**描述**：高亮匹配搜索关键词的节点

**步骤**：
1. 实现 `applyHighlightKeywords()`：
   ```javascript
   function applyHighlightKeywords() {
     if (!graphInstance || !props.highlightKeywords?.length) return

     graphInstance.nodeColor(node => {
       const shouldHighlight = props.highlightKeywords.some(kw =>
         kw.trim() && node.name.toLowerCase().includes(kw.toLowerCase())
       )
       return shouldHighlight
         ? '#ff4d4f'  // Ant Design red-5
         : getDefaultNodeColor(node)
     })
   }
   ```
2. 监听关键词变化：
   ```javascript
   watch(() => props.highlightKeywords, () => {
     if (graphInstance) {
       clearHighlights()
       setTimeout(() => applyHighlightKeywords(), 50)
     }
   }, { deep: true })
   ```

**验证**：
- [x] 搜索"测试"高亮名称中包含"测试"的节点
- [x] 清除搜索移除高亮
- [x] 多个关键词正确高亮

**完成时间**：已完成
**预计耗时**：25 分钟

---

#### 任务 4.2：实现焦点模式
**描述**：仅显示选定节点及其邻居

**步骤**：
1. 实现 `focusNode(id)`：
   ```javascript
   async function focusNode(id) {
     if (!graphInstance || !props.enableFocusNeighbor) return

     const data = graphInstance.graphData()
     const connectedNodeIds = new Set([id])
     const connectedLinkIds = new Set()

     // 查找邻居
     data.links.forEach(link => {
       const sourceId = link.source.id || link.source
       const targetId = link.target.id || link.target

       if (sourceId === id) {
         connectedNodeIds.add(targetId)
         connectedLinkIds.add(link)
       } else if (targetId === id) {
         connectedNodeIds.add(sourceId)
         connectedLinkIds.add(link)
       }
     })

     // 更新可见性
     graphInstance
       .nodeVisibility(node => connectedNodeIds.has(node.id))
       .linkVisibility(link => connectedLinkIds.has(link))
   }
   ```
2. 实现 `clearFocus()`：
   ```javascript
   async function clearFocus() {
     if (!graphInstance) return
     graphInstance
       .nodeVisibility(true)
       .linkVisibility(true)
   }
   ```

**验证**：
- [x] 在详情面板中点击节点触发焦点模式
- [x] 仅连接的节点保持可见
- [x] 点击画布清除焦点并恢复所有节点

**完成时间**：已完成
**预计耗时**：30 分钟

---

#### 任务 4.3：实现适应视图控制
**描述**：添加 `fitView()` 和 `fitCenter()` 方法

**步骤**：
1. 实现 `fitView()`：
   ```javascript
   function fitView() {
     if (!graphInstance) return

     // 计算所有节点的边界框
     const data = graphInstance.graphData()
     if (!data.nodes.length) return

     const distance = 300  // 根据图大小调整
     graphInstance.cameraPosition(
       { x: 0, y: 0, z: distance },
       { x: 0, y: 0, z: 0 },
       1000  // 过渡持续时间
     )
   }
   ```
2. 实现 `fitCenter()`：
   ```javascript
   function fitCenter() {
     if (!graphInstance) return
     graphInstance.cameraPosition(
       { x: 0, y: 0, z: 300 },
       { x: 0, y: 0, z: 0 },
       500
     )
   }
   ```

**验证**：
- [x] 从父组件调用 `fitView()` 使图居中
- [x] 相机平滑动画到新位置
- [x] 添加/删除节点后正常工作

**完成时间**：已完成
**预计耗时**：20 分钟

---

### 阶段 5：主题与响应式
**目标**：处理主题切换和容器调整大小

#### 任务 5.1：实现主题切换
**描述**：主题变化时更新颜色（明暗模式）

**步骤**：
1. 监听主题存储：
   ```javascript
   watch(() => themeStore.isDark, () => {
     if (graphInstance) {
       // 动态更新颜色
       graphInstance
         .nodeColor(node => getNodeColorDynamic(node))
         .linkColor(getCSSVariable('--gray-400'))
     }
   })
   ```
2. 提取动态颜色函数：
   ```javascript
   function getNodeColorDynamic(node) {
     // 检查是否高亮
     if (isNodeHighlighted(node)) {
       return '#ff4d4f'
     }
     // 使用主题感知颜色
     return getCSSVariable('--gray-700')
   }
   ```

**验证**：
- [x] 切换到暗黑模式更新节点/连接颜色
- [x] 无完全图重新渲染（平滑过渡）
- [x] 高亮节点保持高亮颜色

**完成时间**：已完成
**预计耗时**：20 分钟

---

#### 任务 5.2：处理容器调整大小
**描述**：容器调整大小时更新图尺寸

**步骤**：
1. 设置 ResizeObserver：
   ```javascript
   if (window.ResizeObserver) {
     resizeObserver = new ResizeObserver(() => {
       if (!container.value || !graphInstance) return
       const width = container.value.offsetWidth
       const height = container.value.offsetHeight
       graphInstance.width(width).height(height)
     })
     if (container.value) {
       resizeObserver.observe(container.value)
     }
   }
   ```
2. 卸载时清理：
   ```javascript
   onUnmounted(() => {
     if (resizeObserver && container.value) {
       resizeObserver.unobserve(container.value)
     }
   })
   ```

**验证**：
- [x] 调整浏览器窗口更新图大小
- [x] 图保持纵横比
- [x] 调整大小期间无性能问题

**完成时间**：已完成
**预计耗时**：15 分钟

---

#### 任务 5.3：实现 refreshGraph 方法
**描述**：按需完全重新渲染图

**步骤**：
1. 实现 `refreshGraph()`：
   ```javascript
   function refreshGraph() {
     if (graphInstance) {
       graphInstance._destructor()  // 清理 3d-force-graph
       graphInstance = null
     }
     if (container.value) {
       container.value.innerHTML = ''
     }
     clearTimeout(renderTimeout)
     renderTimeout = setTimeout(() => {
       renderGraph()
     }, 300)
   }
   ```

**验证**：
- [x] 调用 `refreshGraph()` 清除并重新渲染图
- [x] 多次刷新后无内存泄漏
- [x] 主题切换后正常工作

**完成时间**：已完成
**预计耗时**：15 分钟

---

### 阶段 6：测试与打磨
**目标**：确保功能对等和性能

#### 任务 6.1：测试所有消费者组件
**描述**：验证 GraphCanvas 在所有使用上下文中工作

**步骤**：
1. 测试 **GraphView.vue**：
   - 加载示例数据（100、500、1000 节点）
   - 测试搜索高亮
   - 测试节点/边详情面板
   - 测试导出数据功能
2. 测试 **KnowledgeGraphSection.vue**：
   - 验证嵌入式图正确渲染
   - 检查响应式布局
3. 测试 **KnowledgeGraphTool.vue**：
   - 验证智能体生成的图显示
   - 测试小数据集（< 50 节点）

**验证**：
- [x] 所有消费者渲染无错误
- [x] 无布局回归
- [x] 与 G6 版本功能对等

**完成时间**：已完成 (详见 TEST_REPORT.md)

---

#### 任务 6.2：性能测试
**描述**：使用大型数据集基准测试渲染性能

**步骤**：
1. 创建测试数据集：
   - 500 节点，800 边
   - 1000 节点，1500 边
   - 2000 节点，3000 边
2. 测量指标：
   - 初始渲染时间
   - 交互期间的 FPS（缩放、旋转）
   - 内存使用
3. 与 G6 基准对比

**验证**：
- [ ] 1000 节点图在 < 3 秒内渲染
- [ ] 交互期间保持 60 FPS
- [ ] 内存使用稳定（无泄漏）
- [ ] 性能优于 G6

**预计耗时**：30 分钟

---

#### 任务 6.3：添加加载状态
**描述**：图初始化期间显示加载指示器

**步骤**：
1. 添加加载 prop/state：
   ```javascript
   const loading = ref(true)
   ```
2. 预热期间显示旋转器：
   ```javascript
   graph.onEngineTick(() => {
     if (graph.engineStopped()) {
       loading.value = false
       emit('data-rendered')
     }
   })
   ```
3. 向模板添加加载覆盖层：
   ```vue
   <div v-if="loading" class="loading-overlay">
     <a-spin size="large" />
   </div>
   ```

**验证**：
- [x] 初始渲染期间出现加载旋转器
- [x] 布局稳定时旋转器消失
- [x] 数据更新期间无闪烁

**完成时间**：已完成

---

#### 任务 6.4：错误处理与降级
**描述**：处理 WebGL 不可用和边缘情况

**步骤**：
1. 检查 WebGL 支持：
   ```javascript
   function checkWebGLSupport() {
     try {
       const canvas = document.createElement('canvas')
       return !!canvas.getContext('webgl') || !!canvas.getContext('experimental-webgl')
     } catch (e) {
       return false
     }
   }
   ```
2. 如不可用显示降级消息：
   ```vue
   <div v-if="!webglSupported" class="webgl-error">
     <a-alert type="warning" message="您的浏览器不支持 WebGL，无法渲染 3D 图谱" />
   </div>
   ```
3. 优雅处理空数据集

**验证**：
- [x] WebGL 不可用时显示适当错误
- [x] 空图显示空状态
- [x] 边缘情况下无控制台错误

**完成时间**：已完成

---

#### 任务 6.5：文档更新
**描述**：更新内联注释和暴露方法文档

**步骤**：
1. 为所有公共方法添加 JSDoc 注释
2. 更新 prop 描述
3. 记录 3D 特定功能（相机控制）
4. 为复杂转换添加代码注释

**验证**：
- [x] 代码文档完善
- [x] Prop 类型匹配实际使用
- [x] 方法签名有文档

**完成时间**：已完成

---

---

## 总结

**总任务数**：23
**预计总时间**：7-8 小时

### 依赖关系
任务必须按阶段顺序完成，但阶段内的任务可以在适用的情况下并行化。

### 关键路径
1. 阶段 1（基础）→ 阶段 2（样式）→ 阶段 3（交互）→ 阶段 4（高级功能）→ 阶段 5（主题）→ 阶段 6（测试）

### 验证检查点
- ✅ 阶段 1 后：基本 3D 图渲染
- ✅ 阶段 2 后：视觉外观匹配 G6
- ✅ 阶段 3 后：所有交互工作
- ✅ 阶段 4 后：功能对等完成
- ✅ 阶段 5 后：主题感知和响应式
- ✅ 阶段 6 后：生产就绪

### 风险缓解
- 开始前备份原始 GraphCanvas.vue
- 每个任务完成后立即测试
- 保持 git 提交小而原子化，便于回滚
- 使用真实生产数据测试（各种节点数）
