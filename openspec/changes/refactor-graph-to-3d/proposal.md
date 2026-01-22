# 提案：知识图谱可视化重构为 3D

## 变更 ID
`refactor-graph-to-3d`

## 概述
将当前使用 @antv/g6 的 2D 知识图谱可视化替换为 3d-force-graph 库，以解决渲染超过 1000 个节点时的严重性能下降问题。新实现将提供沉浸式 3D 可视化，同时保持所有现有功能，包括节点/边交互、搜索高亮和主题支持。

## 问题陈述
当前基于 @antv/g6 构建的知识图谱可视化在节点数量超过 1000 时会遇到严重的性能问题。用户会遇到：
- 严重的 UI 卡顿和帧率下降
- 交互无响应（点击、拖拽、缩放）
- 初始渲染时间过长
- 探索大型知识库时用户体验差

这影响了平台的核心价值主张，即探索和可视化从文档集合中提取的复杂知识图谱。

## 提议的解决方案
从 @antv/g6（基于 2D canvas）迁移到 3d-force-graph（基于 WebGL 的 3D 可视化）：

**为什么选择 3d-force-graph？**
- **性能**：WebGL/ThreeJS 渲染可高效处理 4000+ 节点，如库示例所示
- **力导向布局**：内置 d3-force-3d 物理引擎与当前布局算法匹配
- **丰富的交互**：原生支持节点点击、悬停、拖拽和相机控制
- **可定制性**：灵活的节点/连接样式、标签和 3D 对象渲染
- **现代化技术栈**：活跃维护、TypeScript 支持、完善的文档

**迁移策略**：
1. 替换 GraphCanvas.vue 实现，同时保留其 props API
2. 保持与现有消费者（GraphView.vue、KnowledgeGraphSection.vue 等）的向后兼容性
3. 保持相同的数据格式（nodes/edges 结构）来自后端 API
4. 保留所有面向用户的功能（搜索高亮、焦点模式、详情面板集成）

## 范围

### 包含在内
- 在 GraphCanvas.vue 中用 3d-force-graph 替换 @antv/g6
- 更新 package.json 依赖
- 实现所有当前功能的 3D 等效版本：
  - 节点/边点击事件
  - 搜索关键词高亮
  - 焦点模式（显示节点及其邻居）
  - 主题感知颜色
  - 适应视图/居中视图控制
  - 统计面板覆盖层
- 保持现有组件 API（props、事件、暴露的方法）
- 1000+ 节点图的性能优化

### 不包含在内
- 更改后端图 API 或数据结构
- 修改 GraphDetailPanel.vue 或其他消费者组件
- 超出当前功能的新图分析特性
- 更改其他图相关组件（除非它们直接导入 GraphCanvas）

## 影响分析

### 需要修改的文件
- `web/src/components/GraphCanvas.vue` - 完全重构（424 行）
- `web/package.json` - 更新依赖

### 需要审查的文件（消费者）
- `web/src/views/GraphView.vue` - 主图可视化页面
- `web/src/components/KnowledgeGraphSection.vue` - 知识图谱区域组件
- `web/src/components/ToolCallingResult/tools/KnowledgeGraphTool.vue` - 智能体工具结果显示
- `web/src/composables/useGraph.js` - 图状态管理组合式函数

### 依赖关系
**移除**：
- `@antv/g6: ^5.0.49`

**添加**：
- `3d-force-graph: ^1.73.5`（最新稳定版）
- `three: ^0.160.0`（ThreeJS 对等依赖）

## 技术考虑

### API 兼容性
重构后的 GraphCanvas.vue 将保持相同的 props 接口：
```vue
<GraphCanvas
  :graph-data="{ nodes, edges }"
  :graph-info="{ node_count, edge_count }"
  :highlight-keywords="[]"
  :label-field="'name'"
  :size-by-degree="true"
  @node-click="handler"
  @edge-click="handler"
  @canvas-click="handler"
/>
```

暴露的方法保持不变：
- `refreshGraph()`
- `fitView()`
- `fitCenter()`
- `getInstance()`
- `focusNode(id)`
- `clearFocus()`
- `setData(data)`
- `applyHighlightKeywords()`
- `clearHighlights()`

### 数据格式映射
当前 G6 格式 → 3d-force-graph 格式：

```javascript
// 当前（G6）
{
  nodes: [{ id: "1", data: { label: "节点 A", degree: 3 } }],
  edges: [{ id: "e1", source: "1", target: "2", data: { label: "关联" } }]
}

// 3d-force-graph（内部转换）
{
  nodes: [{ id: "1", name: "节点 A", degree: 3, val: 15 }],
  links: [{ source: "1", target: "2", label: "关联" }]
}
```

### 功能对等矩阵
| 功能 | G6（当前） | 3d-force-graph（计划） | 实现说明 |
|---------|--------------|--------------------------|---------------------|
| 力导向布局 | d3-force (2D) | d3-force-3d | 直接替换 |
| 节点点击 | ✅ | ✅ | `onNodeClick()` |
| 边点击 | ✅ | ✅ | `onLinkClick()` |
| 画布点击 | ✅ | ✅ | 空白处点击检测 |
| 关键词高亮 | ✅ | ✅ | 节点颜色/透明度变化 |
| 焦点模式 | ✅ | ✅ | 通过 `nodeVisibility()` 显示/隐藏节点 |
| 主题切换 | ✅ | ✅ | 动态颜色更新 |
| 按度数调整大小 | ✅ | ✅ | 映射度数到 `nodeVal()` |
| 节点标签 | ✅ | ✅ | `nodeLabel()` 访问器 |
| 边标签 | ✅ | ✅ | `linkLabel()` 访问器 |
| 拖拽和缩放 | ✅ | ✅ | 内置相机控制 |
| 适应视图 | ✅ | ✅ | 相机位置动画 |
| 自动调整大小 | ✅ | ✅ | 容器调整大小时手动更新大小 |
| 统计覆盖层 | ✅ | ✅ | 插槽内容不变 |

### 性能期望
基于 3d-force-graph 的能力：
- **当前（G6）**：1000+ 节点时卡顿
- **目标（3d-force-graph）**：流畅渲染高达 4000+ 节点
- **渲染时间**：中等硬件上 1000 节点 < 2 秒
- **交互延迟**：点击/悬停 < 16ms（60 FPS）

### 风险与缓解措施
| 风险 | 影响 | 缓解措施 |
|------|--------|------------|
| 3D UX 学习曲线 | 用户不熟悉 3D 控制 | 添加细微的相机控制提示；提供直观的默认设置 |
| G6 功能缺失 | 功能对等差距 | 实施前全面映射所有 G6 功能；尽早标记差距 |
| ThreeJS 打包大小 | web 打包体积增加 | 使用 tree-shaking；考虑对图路由进行懒加载 |
| 浏览器兼容性 | 不支持 WebGL 的旧浏览器 | 添加 WebGL 检测；显示降级消息 |

## 实施阶段

### 阶段 1：基础（核心 3D 渲染）
- 安装依赖
- 创建基本的 3d-force-graph 集成
- 实现数据转换层
- 设置力布局参数

### 阶段 2：功能对等（交互与样式）
- 节点/边/画布点击事件
- 主题感知颜色系统
- 基于度数的节点大小调整
- 节点和边标签
- 相机控制（缩放、旋转、平移）

### 阶段 3：高级功能（高亮与焦点）
- 关键词搜索高亮
- 焦点模式（显示节点 + 邻居）
- 适应视图/居中视图方法
- 容器变化时自动调整大小

### 阶段 4：打磨与优化（性能与 UX）
- 使用 1000-5000 节点数据集进行性能测试
- 相机动画平滑处理
- 数据更新期间的加载状态
- 错误边界和降级方案

## 成功标准
- [ ] 所有 8 个暴露的方法与当前实现工作方式相同
- [ ] 所有 3 个事件处理器使用相同的数据结构发出
- [ ] 关键词高亮为高亮节点添加动画/脉冲效果
- [ ] 焦点模式正确隐藏无关节点
- [ ] 主题切换更新图颜色而无需完全重新渲染
- [ ] 2000 节点图在 < 3 秒内渲染
- [ ] 1000 节点图在缩放/旋转期间保持 60 FPS
- [ ] 任何消费者组件（GraphView.vue 等）无回归
- [ ] 统计覆盖层保持可见且准确

## 待定问题
1. 是否应为喜欢旧视图的用户提供 2D/3D 切换？ → **决定：否**，保持实现简单；3D 是性能修复
2. 我们需要保留节点类型的完全相同的调色板吗？ → **决定：是**，使用现有的 CSS 变量
3. 边箭头是否应在 3D 中渲染？ → **决定：是**，使用内置的 `linkDirectionalArrowLength`
4. 如何处理 3D 空间中非常长的节点标签？ → **决定：截断为 20 个字符；在详情面板中显示完整标签**

## 批准检查清单
- [ ] 前端团队审查提案
- [ ] 确认性能要求（1000+ 节点目标）
- [ ] UX 批准 3D 可视化方法
- [ ] 评估破坏性变更（预计无）
- [ ] 估算时间线（见 tasks.md）
