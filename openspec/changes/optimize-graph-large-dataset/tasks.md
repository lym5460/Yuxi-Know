# 任务清单：优化知识图谱大数据集性能并清理冗余依赖

## 变更 ID
`optimize-graph-large-dataset`

## 任务序列

### 阶段 1：清理冗余依赖

#### 任务 1.1：移除未使用的图可视化依赖
**描述**：从 package.json 移除 sigma/graphology 相关依赖

**步骤**：
1. 编辑 `web/package.json`，移除以下依赖：
   ```json
   "@sigma/edge-curve": "^3.1.0",
   "@sigma/node-border": "^3.0.0",
   "sigma": "^3.0.2",
   "graphology": "^0.26.0",
   "graphology-generators": "^0.11.2"
   ```
2. 在宿主机运行 `cd web && pnpm install` 更新 lockfile
3. 检查 `pnpm list` 确认依赖已移除

**验证**：
- [ ] `web/package.json` 中不再包含 sigma/graphology 相关依赖
- [ ] `pnpm list sigma` 返回未找到
- [ ] `pnpm list graphology` 返回未找到
- [ ] 应用仍可正常启动，无控制台错误

**预计耗时**：10 分钟

---

#### 任务 1.2：删除未使用的文件
**描述**：删除 graphStore.js 和 sigma.css

**步骤**：
1. 确认 `graphStore.js` 未被引用：
   ```bash
   grep -r "graphStore" web/src --exclude-dir=node_modules
   ```
2. 删除文件：
   - `web/src/stores/graphStore.js`
   - `web/src/assets/css/sigma.css`
3. 从 `web/src/assets/css/main.css` 中移除 sigma.css 导入（如果有）

**验证**：
- [ ] 文件已删除
- [ ] `main.css` 中无 sigma.css 导入
- [ ] 应用仍可正常运行

**预计耗时**：5 分钟

---

### 阶段 2：优化 3d-force-graph 性能配置

#### 任务 2.1：实现数据量级自适应配置
**描述**：根据节点数量动态调整 3d-force-graph 渲染参数

**步骤**：
1. 在 `GraphCanvas.vue` 的 `initGraph()` 函数中添加数据量级检测：
   ```javascript
   function getOptimizedConfig(nodeCount) {
     if (nodeCount > 2000) {
       return {
         nodeRelSize: 1.5,
         linkOpacity: 0.2,
         warmupTicks: 30,
         cooldownTicks: 50,
         d3AlphaDecay: 0.03,
         d3VelocityDecay: 0.2,
         nodeResolution: 8,  // 降低节点几何复杂度
         enableNodeLabels: false // 大数据集禁用标签
       }
     } else if (nodeCount > 1000) {
       return {
         nodeRelSize: 2,
         linkOpacity: 0.3,
         warmupTicks: 50,
         cooldownTicks: 100,
         d3AlphaDecay: 0.02,
         d3VelocityDecay: 0.3,
         nodeResolution: 12,
         enableNodeLabels: false
       }
     } else if (nodeCount > 500) {
       return {
         nodeRelSize: 3,
         linkOpacity: 0.4,
         warmupTicks: 80,
         cooldownTicks: 150,
         d3AlphaDecay: 0.015,
         d3VelocityDecay: 0.4,
         nodeResolution: 16,
         enableNodeLabels: true
       }
     } else {
       return {
         nodeRelSize: 4,
         linkOpacity: 0.5,
         warmupTicks: 100,
         cooldownTicks: 200,
         d3AlphaDecay: 0.01,
         d3VelocityDecay: 0.4,
         nodeResolution: 16,
         enableNodeLabels: true
       }
     }
   }
   ```

2. 在 `initGraph()` 中应用配置：
   ```javascript
   const data = formatData()
   const config = getOptimizedConfig(data.nodes.length)
   
   graphInstance = ForceGraph3D()(container.value)
     .width(width)
     .height(height)
     .backgroundColor(getCSSVariable('--gray-0'))
     .nodeRelSize(config.nodeRelSize)
     .linkOpacity(config.linkOpacity)
     .warmupTicks(config.warmupTicks)
     .cooldownTicks(config.cooldownTicks)
     .d3AlphaDecay(config.d3AlphaDecay)
     .d3VelocityDecay(config.d3VelocityDecay)
     .nodeResolution(config.nodeResolution)
   ```

**验证**：
- [ ] 小数据集（< 500）：高质量渲染，标签可见
- [ ] 中数据集（500-1000）：良好质量，标签可见
- [ ] 大数据集（1000-2000）：性能优先，标签隐藏
- [ ] 超大数据集（> 2000）：最大性能优化

**预计耗时**：30 分钟

---

#### 任务 2.2：优化节点标签渲染策略
**描述**：大数据集时动态调整标签显示策略

**步骤**：
1. 修改 `nodeThreeObject` 配置，添加条件判断：
   ```javascript
   .nodeThreeObject(node => {
     // 根据配置决定是否显示标签
     if (!config.enableNodeLabels) return null
     
     const sprite = new SpriteText(node.name)
     sprite.color = getCSSVariable('--gray-900')
     sprite.textHeight = 8
     sprite.backgroundColor = 'rgba(255, 255, 255, 0.9)'
     sprite.padding = 2
     sprite.borderRadius = 3
     sprite.borderWidth = 1
     sprite.borderColor = 'rgba(0, 0, 0, 0.1)'
     sprite.position.x = 0
     sprite.position.y = node.val + 4
     sprite.position.z = 0
     return sprite
   })
   .nodeThreeObjectExtend(true)
   ```

2. 添加悬停时显示标签的逻辑（大数据集场景）：
   ```javascript
   let hoverNode = null
   
   .onNodeHover(node => {
     if (!config.enableNodeLabels && node) {
       // 大数据集时，仅悬停显示标签
       container.value.style.cursor = node ? 'pointer' : 'default'
       hoverNode = node
       // 可选：更新 tooltip
     }
   })
   ```

**验证**：
- [ ] < 500 节点：所有标签始终可见
- [ ] 500-1000 节点：所有标签始终可见
- [ ] > 1000 节点：标签隐藏，悬停时通过 tooltip 显示
- [ ] 标签显示/隐藏不影响其他功能

**预计耗时**：25 分钟

---

#### 任务 2.3：优化力导向布局参数
**描述**：调整 d3-force-3d 物理参数以加快收敛速度

**步骤**：
1. 在 `initGraph()` 中优化力参数配置：
   ```javascript
   graphInstance
     .d3Force('charge', d3.forceManyBody()
       .strength(nodeCount > 1000 ? -200 : -400)
       .distanceMax(nodeCount > 1000 ? 400 : 600)
     )
     .d3Force('link', d3.forceLink()
       .distance(nodeCount > 1000 ? 60 : 100)
       .strength(nodeCount > 1000 ? 0.5 : 0.8)
     )
     .d3Force('center', d3.forceCenter())
     .d3Force('collide', d3.forceCollide()
       .radius(nodeCount > 1000 ? 20 : 40)
       .strength(nodeCount > 1000 ? 0.5 : 0.8)
     )
   ```

2. 添加引擎停止回调，更新加载状态：
   ```javascript
   .onEngineStop(() => {
     loading.value = false
     console.log('布局引擎已停止')
   })
   ```

**验证**：
- [ ] 小数据集：节点分布均匀，无重叠
- [ ] 大数据集：布局在合理时间内收敛（< 5 秒）
- [ ] 布局稳定后加载状态正确更新

**预计耗时**：20 分钟

---

### 阶段 3：性能监控和用户体验优化

#### 任务 3.1：添加性能监测
**描述**：记录渲染性能指标，便于后续优化

**步骤**：
1. 在 `setGraphData()` 开始时记录时间：
   ```javascript
   const startTime = performance.now()
   const data = formatData()
   const nodeCount = data.nodes.length
   const linkCount = data.links.length
   
   console.log(`开始渲染图谱: ${nodeCount} 节点, ${linkCount} 边`)
   ```

2. 在渲染完成后记录耗时：
   ```javascript
   setTimeout(() => {
     const renderTime = performance.now() - startTime
     console.log(`图谱渲染完成，耗时: ${renderTime.toFixed(0)}ms`)
     
     loading.value = false
     emit('data-rendered', { renderTime, nodeCount, linkCount })
   }, 1500)
   ```

3. 添加性能警告（可选）：
   ```javascript
   if (nodeCount > 3000) {
     console.warn(`大数据集渲染 (${nodeCount} 节点)，可能影响性能`)
   }
   ```

**验证**：
- [ ] 控制台正确显示渲染时间
- [ ] `data-rendered` 事件包含性能指标
- [ ] 大数据集时显示警告信息

**预计耗时**：15 分钟

---

#### 任务 3.2：添加大数据集提示
**描述**：当数据量较大时，向用户显示提示信息

**步骤**：
1. 在 `GraphCanvas.vue` 模板中添加提示区域：
   ```vue
   <div v-if="showPerformanceTip" class="performance-tip">
     <a-alert
       type="info"
       :message="`当前显示 ${graphData.nodes.length} 个节点，已启用性能优化模式`"
       description="大数据集场景下已自动隐藏节点标签，悬停节点可查看详情"
       closable
       @close="showPerformanceTip = false"
     />
   </div>
   ```

2. 添加响应式状态：
   ```javascript
   const showPerformanceTip = ref(false)
   
   watch(() => props.graphData, (newData) => {
     if (newData && newData.nodes && newData.nodes.length > 1000) {
       showPerformanceTip.value = true
     }
   }, { immediate: true })
   ```

**验证**：
- [ ] > 1000 节点时显示提示
- [ ] < 1000 节点时不显示
- [ ] 提示可关闭
- [ ] 刷新页面后重新显示（如果数据仍然很大）

**预计耗时**：15 分钟

---

#### 任务 3.3：优化加载状态显示
**描述**：改善大数据集加载时的用户体验

**步骤**：
1. 更新加载提示文案，显示节点数量：
   ```vue
   <div v-if="loading && webglSupported" class="loading-overlay">
     <a-spin size="large">
       <template #tip>
         <div class="loading-tip">
           正在渲染 {{ graphData.nodes?.length || 0 }} 个节点...
           <div v-if="graphData.nodes?.length > 1000" class="loading-subtip">
             大数据集渲染中，请稍候
           </div>
         </div>
       </template>
     </a-spin>
   </div>
   ```

2. 添加渐进式渲染反馈（可选）：
   ```javascript
   let loadingProgress = ref(0)
   
   .onEngineTick(() => {
     if (!graphInstance.engineStopped()) {
       loadingProgress.value = Math.min(90, loadingProgress.value + 5)
     }
   })
   ```

**验证**：
- [ ] 加载时显示节点数量
- [ ] 大数据集有额外提示
- [ ] 加载完成后正确隐藏

**预计耗时**：20 分钟

---

### 阶段 4：测试与验证

#### 任务 4.1：功能回归测试
**描述**：确保所有现有功能仍然正常工作

**步骤**：
1. 测试 GraphView.vue 页面：
   - [ ] 加载示例数据（100 节点）
   - [ ] 测试搜索高亮功能
   - [ ] 测试节点点击 → 详情面板
   - [ ] 测试边点击 → 边详情
   - [ ] 测试画布点击 → 关闭详情
   - [ ] 测试导出数据功能
   
2. 测试 KnowledgeGraphSection.vue：
   - [ ] 嵌入式图正确渲染
   - [ ] 响应式布局正常
   
3. 测试 KnowledgeGraphTool.vue：
   - [ ] 智能体生成的图正确显示
   - [ ] 小数据集（< 50 节点）正常

**预计耗时**：30 分钟

---

#### 任务 4.2：性能基准测试
**描述**：使用不同规模的数据集测试性能

**步骤**：
1. 准备测试数据集：
   - 100 节点，150 边（小）
   - 500 节点，800 边（中）
   - 1000 节点，1500 边（大）
   - 2000 节点，3000 边（超大）
   - 5000 节点，7500 边（极限）

2. 使用 Chrome DevTools Performance 记录：
   - 初始渲染时间
   - FPS（帧率）
   - 内存使用
   - 交互响应时间（缩放、旋转）

3. 创建性能报告，记录优化前后对比

**验证目标**：
- [ ] 1000 节点：渲染 < 2 秒
- [ ] 1000 节点：交互 FPS > 50
- [ ] 2000 节点：渲染 < 3 秒
- [ ] 2000 节点：交互 FPS > 40
- [ ] 5000 节点：渲染 < 5 秒
- [ ] 5000 节点：交互 FPS > 30

**预计耗时**：40 分钟

---

#### 任务 4.3：浏览器兼容性测试
**描述**：验证不同浏览器的兼容性

**步骤**：
1. 在以下浏览器测试基本功能：
   - [ ] Chrome/Edge (最新版) - 主要测试
   - [ ] Firefox (最新版)
   - [ ] Safari (最新版，如果有 Mac）

2. 验证 WebGL 降级处理：
   - [ ] 禁用 WebGL 后显示错误提示
   - [ ] 错误提示友好且可操作

**预计耗时**：20 分钟

---

#### 任务 4.4：打包体积验证
**描述**：验证移除依赖后的打包体积变化

**步骤**：
1. 构建生产版本：
   ```bash
   cd web && pnpm run build
   ```

2. 检查打包体积：
   ```bash
   ls -lh dist/assets/*.js
   ```

3. 与优化前对比（如果有基准数据）

**验证**：
- [ ] 构建成功，无错误
- [ ] vendor bundle 体积明显减小（预期 ~400KB）
- [ ] 应用功能完整

**预计耗时**：15 分钟

---

## 总结

**总任务数**：14
**预计总时间**：4-5 小时

### 依赖关系
- 阶段 1 必须先完成（清理依赖）
- 阶段 2 的任务可以并行（性能优化）
- 阶段 3 依赖阶段 2（用户体验优化）
- 阶段 4 必须最后进行（测试验证）

### 关键路径
1. 阶段 1（清理）→ 阶段 2（性能优化）→ 阶段 3（UX）→ 阶段 4（测试）

### 验证检查点
- ✅ 阶段 1 后：依赖已移除，应用仍正常运行
- ✅ 阶段 2 后：大数据集性能明显提升
- ✅ 阶段 3 后：用户体验良好，有适当反馈
- ✅ 阶段 4 后：所有功能正常，性能目标达成

### 回滚策略
- 使用 git 进行版本控制
- 每个阶段完成后提交一次
- 如有问题可以按阶段回滚
