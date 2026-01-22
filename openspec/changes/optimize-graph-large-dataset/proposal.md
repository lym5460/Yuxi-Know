# 提案：优化知识图谱大数据集性能并清理冗余依赖

## Why

当前知识图谱可视化在处理大量数据时性能不佳，尤其是节点数超过 1000 时会出现严重卡顿。同时，项目中存在未使用的图可视化库依赖（sigma、graphology 系列），这些依赖增加了打包体积但未被使用。

**核心问题**：
1. **性能问题**：大数据集（1000+ 节点）渲染和交互时出现严重卡顿
2. **依赖冗余**：sigma/graphology 相关库未被使用但仍在 package.json 中
3. **缺乏优化**：3d-force-graph 已集成但未针对大数据集场景进行优化配置

**用户影响**：
- 用户在查看大型知识库的图谱时体验极差
- 不必要的依赖增加首次加载时间和打包体积
- 未能充分发挥 3d-force-graph 的性能优势

## What Changes

### 1. 移除冗余的图可视化依赖

**移除的包**：
- `@sigma/edge-curve: ^3.1.0`
- `@sigma/node-border: ^3.0.0`
- `sigma: ^3.0.2`
- `graphology: ^0.26.0`
- `graphology-generators: ^0.11.2`

**移除的文件**：
- `web/src/stores/graphStore.js` - 未被引用的 sigma 图状态管理
- `web/src/assets/css/sigma.css` - sigma 相关样式

### 2. 优化 3d-force-graph 大数据集性能

基于 [3d-force-graph 官方示例](https://github.com/vasturiano/3d-force-graph/tree/master/example)中的 large-graph 场景最佳实践：

**性能优化策略**：
- 使用 `warmupTicks` 和 `cooldownTicks` 优化力导向布局计算
- 针对大数据集调整力参数（charge、link、collide）
- 实现渐进式渲染，避免一次性加载导致阻塞
- 使用 `nodeRelSize` 控制节点大小，避免过大节点影响性能
- 优化节点标签渲染策略（大数据集时减少标签数量）
- 添加数据量级自适应配置（根据节点数量动态调整渲染参数）

**配置优化**：
```javascript
// 大数据集场景下的优化配置
const nodeCount = data.nodes.length

// 根据数据量级调整参数
if (nodeCount > 1000) {
  graph
    .nodeRelSize(2)  // 缩小节点相对大小
    .linkOpacity(0.3)  // 降低边透明度
    .warmupTicks(50)   // 减少预热帧数
    .cooldownTicks(100) // 减少冷却帧数
    .d3AlphaDecay(0.02) // 加快布局收敛
    .d3VelocityDecay(0.3) // 加快布局收敛
} else if (nodeCount > 500) {
  graph
    .warmupTicks(100)
    .cooldownTicks(150)
} else {
  // 小数据集使用默认配置
  graph
    .warmupTicks(100)
    .cooldownTicks(200)
}
```

### 3. 实现性能监控和降级策略

- 添加性能监测，记录渲染时间
- 大数据集时显示警告提示
- 提供"精简模式"开关（隐藏标签、简化样式）

## Impact

### 修改的文件
- `web/package.json` - 移除 sigma/graphology 依赖
- `web/src/components/GraphCanvas.vue` - 添加大数据集优化配置
- `web/pnpm-lock.yaml` - 自动更新

### 删除的文件
- `web/src/stores/graphStore.js`
- `web/src/assets/css/sigma.css`

### 影响的组件（需验证兼容性）
- `web/src/views/GraphView.vue` - 主图谱页面
- `web/src/components/KnowledgeGraphSection.vue` - 知识库图谱区域
- `web/src/components/ToolCallingResult/tools/KnowledgeGraphTool.vue` - 工具调用结果

### 性能预期

**当前（未优化）**：
- 1000 节点：渲染 5-8 秒，交互卡顿
- 2000 节点：渲染 10+ 秒，严重卡顿

**目标（优化后）**：
- 1000 节点：渲染 < 2 秒，流畅交互（60 FPS）
- 2000 节点：渲染 < 3 秒，流畅交互
- 5000 节点：渲染 < 5 秒，可接受的交互性能（30+ FPS）

### 打包体积优化

**移除依赖后预期减少**：
- sigma: ~200KB (minified)
- graphology: ~150KB (minified)
- 相关依赖: ~100KB
- **总计减少**: ~450KB (minified)，约 ~1.2MB (gzipped 前)

## 破坏性变更

**无破坏性变更** - 移除的 sigma/graphology 代码未被使用，不影响现有功能。

## 测试策略

### 功能测试
- [ ] 小数据集（< 100 节点）：功能正常，无回归
- [ ] 中数据集（100-500 节点）：功能正常，性能良好
- [ ] 大数据集（500-1000 节点）：功能正常，性能可接受
- [ ] 超大数据集（1000-5000 节点）：功能正常，性能降级提示

### 性能基准测试
使用 Chrome DevTools Performance 记录：
- FPS (帧率)
- 渲染时间
- 内存使用
- 交互响应时间

### 兼容性测试
- [ ] Chrome/Edge (最新版)
- [ ] Firefox (最新版)
- [ ] Safari (最新版)
- [ ] WebGL 不支持场景的降级提示

## 参考资料

- [3d-force-graph 官方文档](https://github.com/vasturiano/3d-force-graph)
- [3d-force-graph large-graph 示例](https://github.com/vasturiano/3d-force-graph/tree/master/example)
- [3d-force-graph API 文档](https://github.com/vasturiano/3d-force-graph#api-reference)
- 本地测试文件：`web/3d-force-test/test.html`（使用 blocks.json 大数据集）
