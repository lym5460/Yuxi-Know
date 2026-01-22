# 设计文档：优化知识图谱大数据集性能

## Context

当前 Yuxi-Know 知识图谱可视化使用 3d-force-graph (基于 WebGL/ThreeJS) 进行渲染。虽然已经从 @antv/g6 迁移，但仍存在两个主要问题：

1. **性能配置未优化**：使用默认配置，未针对不同规模数据集进行调优
2. **冗余依赖**：历史遗留的 sigma/graphology 库未被移除，增加打包体积

### 技术背景

**3d-force-graph 架构**：
- 基于 ThreeJS WebGL 渲染
- 使用 d3-force-3d 物理引擎进行力导向布局
- 支持自定义节点/边渲染（Three.js 对象）
- 提供丰富的配置选项用于性能调优

**当前性能瓶颈**：
1. **布局计算**：warmupTicks/cooldownTicks 过高导致渲染时间长
2. **节点标签**：使用 SpriteText 创建 3D 文本精灵，大数据集时开销大
3. **几何复杂度**：nodeResolution 过高（16）导致渲染压力
4. **物理模拟**：力参数未根据数据规模调整

## Goals / Non-Goals

### Goals
1. **性能优化**：1000+ 节点时保持流畅交互（> 30 FPS）
2. **自适应配置**：根据数据规模自动调整渲染参数
3. **减小打包体积**：移除未使用的 sigma/graphology 依赖（~450KB）
4. **用户体验**：提供性能反馈，让用户了解大数据集状态

### Non-Goals
- 不改变图谱的交互方式和用户界面
- 不添加新的可视化功能（如聚类、过滤等）
- 不修改后端 API 或数据格式
- 不支持超过 10,000 节点的数据集（WebGL 限制）

## Decisions

### 决策 1：数据量级分级策略

**方案**：根据节点数量将数据集分为 4 个等级

| 级别 | 节点数 | 渲染质量 | 标签策略 | warmupTicks | nodeResolution |
|------|--------|----------|----------|-------------|----------------|
| 小 | < 500 | 高 | 始终显示 | 100 | 16 |
| 中 | 500-1000 | 高 | 始终显示 | 80 | 16 |
| 大 | 1000-2000 | 中 | 悬停显示 | 50 | 12 |
| 超大 | > 2000 | 低 | 悬停显示 | 30 | 8 |

**理由**：
- 渐进式降低质量，避免突然的用户体验断层
- 保留小中数据集的高质量体验（大部分用例）
- 大数据集时优先保证可用性而非美观

**替代方案考虑**：
- ❌ 固定配置：无法兼顾不同规模的性能和质量
- ❌ 用户手动选择：增加认知负担，大多数用户不知道如何选择
- ✅ 自适应配置：对用户透明，自动优化

### 决策 2：节点标签渲染策略

**方案**：大数据集（> 1000 节点）时默认隐藏标签，悬停时通过 tooltip 显示

**实现**：
```javascript
// < 1000 节点：使用 SpriteText 3D 标签
.nodeThreeObject(node => {
  const sprite = new SpriteText(node.name)
  // ... 配置
  return sprite
})

// > 1000 节点：返回 null，不渲染标签
.nodeThreeObject(node => null)

// 使用 onNodeHover + HTML tooltip 显示悬停信息
.onNodeHover(node => {
  if (node) {
    showTooltip(node.name, event.pageX, event.pageY)
  } else {
    hideTooltip()
  }
})
```

**理由**：
- SpriteText 是性能瓶颈（每个节点一个 Three.js 对象）
- HTML tooltip 性能开销极小，且可以显示更丰富信息
- 悬停交互符合用户预期（与桌面应用一致）

**权衡**：
- ✅ 性能提升显著（减少 1000+ Three.js 对象）
- ❌ 牺牲了"一览全局"的能力（但大数据集时标签重叠也不可读）

### 决策 3：力导向布局参数调优

**方案**：根据数据规模动态调整 d3-force-3d 参数

```javascript
// 大数据集（> 1000 节点）
.d3Force('charge', d3.forceManyBody()
  .strength(-200)  // 减弱斥力（加快收敛）
  .distanceMax(400)  // 缩小作用范围
)
.d3Force('link', d3.forceLink()
  .distance(60)  // 缩短边长度
  .strength(0.5)  // 降低边强度
)
.d3AlphaDecay(0.03)  // 加快模拟衰减
.d3VelocityDecay(0.2)  // 加快速度衰减
```

**理由**：
- 大数据集时，精确布局的边际收益递减
- 快速收敛 > 完美布局（用户可以手动调整）
- 参考 3d-force-graph 官方 large-graph 示例

### 决策 4：依赖清理策略

**方案**：直接移除 sigma/graphology 所有相关代码和依赖

**影响分析**：
- `graphStore.js`：未被任何组件导入 ✅ 安全删除
- `sigma.css`：仅在 `main.css` 中导入 ✅ 安全删除
- package.json 依赖：未被代码使用 ✅ 安全删除

**验证**：
```bash
# 确认无引用
grep -r "graphStore" web/src --exclude-dir=node_modules
grep -r "sigma" web/src --exclude-dir=node_modules --exclude="*.css"
grep -r "graphology" web/src --exclude-dir=node_modules
```

**回滚策略**：
- Git 版本控制，可随时恢复
- 保留 GraphCanvas.vue.backup 作为参考

## Risks / Trade-offs

### 风险 1：大数据集交互体验下降

**风险**：> 2000 节点时，即使优化后仍可能出现卡顿

**缓解措施**：
1. 添加性能提示，告知用户当前数据量级
2. 建议用户使用搜索/筛选功能减少显示节点
3. 考虑后端分页加载（未来优化）

**影响评估**：中等 - 大多数用户不会遇到超大数据集

### 风险 2：移除依赖导致未知回归

**风险**：可能存在未被测试到的 sigma/graphology 使用场景

**缓解措施**：
1. 全面搜索代码库确认无引用
2. 完整的功能回归测试
3. 在开发环境先验证一周

**影响评估**：低 - 代码搜索未发现任何引用

### 权衡 3：标签隐藏 vs 性能

**权衡**：大数据集时牺牲标签可见性换取性能

**替代方案**：
- 方案 A：缩小标签字体（仍有性能问题）
- 方案 B：仅显示部分标签（用户困惑：为什么有些节点没标签？）
- **✅ 方案 C**：完全隐藏，悬停显示（清晰的交互模式）

**用户反馈机制**：
- 显示提示信息："大数据集模式：悬停节点查看详情"
- 提供反馈入口，收集用户意见

## Migration Plan

### 第一步：清理依赖（无风险）
1. 移除 package.json 依赖
2. 删除未使用文件
3. 运行完整测试套件
4. **检查点**：所有测试通过 → 继续

### 第二步：添加性能优化（低风险）
1. 实现数据量级检测函数
2. 应用自适应配置
3. 优化力导向参数
4. **检查点**：小数据集无回归 → 继续

### 第三步：优化标签渲染（中风险）
1. 实现条件标签渲染
2. 添加 tooltip 逻辑
3. 测试不同数据规模
4. **检查点**：用户体验可接受 → 继续

### 第四步：性能测试和调优（低风险）
1. 基准测试各规模数据集
2. 微调参数阈值
3. 添加性能监控
4. **检查点**：性能目标达成 → 完成

### 回滚策略
- 每步完成后 git commit
- 如任何检查点失败，回滚到上一步
- 保留 GraphCanvas.vue.backup 作为最后手段

## Open Questions

1. **Q**: 是否需要提供"性能模式"和"质量模式"手动切换？
   **A**: 暂不需要，自适应配置对大多数用户够用。如有反馈可后续添加。

2. **Q**: 超过 5000 节点时是否应该拒绝渲染或强制分页？
   **A**: 先观察实际使用情况。当前策略是允许渲染但性能降级。

3. **Q**: 是否需要持久化用户的性能偏好设置？
   **A**: 不需要，自适应配置即可。用户偏好可作为未来增强。

## Performance Targets

### 渲染时间（从调用 setGraphData 到 onEngineStop）

| 节点数 | 当前 | 目标 | 方法 |
|--------|------|------|------|
| 500 | ~2s | < 1s | 默认配置 |
| 1000 | ~5s | < 2s | 减少 ticks |
| 2000 | ~10s | < 3s | 激进优化 |
| 5000 | >20s | < 5s | 最大优化 |

### 交互帧率（缩放、旋转时）

| 节点数 | 当前 | 目标 |
|--------|------|------|
| 500 | 60 FPS | 60 FPS |
| 1000 | ~30 FPS | > 50 FPS |
| 2000 | ~15 FPS | > 40 FPS |
| 5000 | < 10 FPS | > 30 FPS |

### 内存使用

| 节点数 | 预期内存增长 |
|--------|--------------|
| 1000 | < 100 MB |
| 2000 | < 200 MB |
| 5000 | < 500 MB |

## References

- [3d-force-graph API Reference](https://github.com/vasturiano/3d-force-graph#api-reference)
- [3d-force-graph Large Graph Example](https://github.com/vasturiano/3d-force-graph/tree/master/example)
- [d3-force-3d Documentation](https://github.com/vasturiano/d3-force-3d)
- [ThreeJS Performance Tips](https://discoverthreejs.com/tips-and-tricks/)
- 本地测试：`web/3d-force-test/test.html`（包含 ~16K 节点的 blocks.json）
