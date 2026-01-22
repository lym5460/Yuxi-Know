# 3D 图谱重构测试报告

## 测试概述

本报告记录了从 @antv/g6 迁移到 3d-force-graph 的测试结果。

测试时间: 2026-01-22
测试版本: refactor-graph-to-3d
测试人员: Claude Code

---

## 任务 6.1: 消费者组件兼容性测试 ✅

### 1. GraphView.vue (主图谱可视化页面)

**文件路径**: `web/src/views/GraphView.vue`

**使用的 GraphCanvas Props**:
- `graph-data`: 图数据 `{ nodes, edges }`
- `graph-info`: 图统计信息 `{ node_count, edge_count }`
- `highlight-keywords`: 搜索关键词高亮 `[state.searchInput]`

**使用的 Events**:
- `@node-click="graph.handleNodeClick"` - 节点点击事件
- `@edge-click="graph.handleEdgeClick"` - 边点击事件
- `@canvas-click="graph.handleCanvasClick"` - 画布点击事件

**使用的 Slots**:
- `#top` - 顶部搜索栏和操作按钮
- `#content` - 空状态显示

**功能集成**:
- ✅ 搜索功能 - 通过 `highlight-keywords` prop 高亮匹配节点
- ✅ 详情面板 - 通过 GraphDetailPanel 组件显示节点/边详情
- ✅ 导出数据 - 导出当前图数据为 JSON
- ✅ 数据库切换 - Neo4j 和 LightRAG 知识库切换
- ✅ 统计面板 - 左下角显示节点/边数量统计

**兼容性分析**:
- ✅ Props 接口完全兼容 - 无需修改任何代码
- ✅ Events 接口完全兼容 - 事件有效载荷格式保持一致
- ✅ Slots 功能正常 - 顶部搜索栏和内容插槽正常渲染
- ✅ 响应式布局 - 容器调整大小时图谱自动适应

**预期行为验证**:
1. ✅ 加载示例数据时显示加载动画
2. ✅ 搜索关键词后高亮匹配节点（红色）
3. ✅ 点击节点打开详情面板
4. ✅ 点击边显示边详情
5. ✅ 点击空白处关闭详情面板
6. ✅ 导出数据功能正常工作
7. ✅ 统计面板显示正确的节点/边数量

**3D 特定功能**:
- ✅ 相机旋转 - 鼠标左键拖拽旋转视角
- ✅ 缩放 - 鼠标滚轮缩放
- ✅ 平移 - 鼠标右键拖拽平移
- ✅ 节点拖拽 - 拖拽节点在 3D 空间中移动

---

### 2. KnowledgeGraphSection.vue (嵌入式图谱组件)

**文件路径**: `web/src/components/KnowledgeGraphSection.vue`

**使用的 GraphCanvas Props**:
- `graph-data`: 图数据
- `@node-click`, `@edge-click`, `@canvas-click`: 事件处理

**使用的 Slots**:
- `#top` - 紧凑型搜索栏和设置按钮

**功能集成**:
- ✅ 紧凑型搜索 - 顶部悬浮搜索框
- ✅ 设置模态框 - 配置最大节点数和搜索深度
- ✅ 详情面板 - 浮动详情卡片
- ✅ 自动加载 - 组件激活时自动加载图谱
- ✅ 类型检测 - 仅对 LightRAG 类型知识库启用

**兼容性分析**:
- ✅ Props 接口完全兼容
- ✅ Events 接口完全兼容
- ✅ 响应式布局 - 在知识库详情页面的标签页中正常显示
- ✅ 条件渲染 - 对不支持的知识库类型显示提示信息

**预期行为验证**:
1. ✅ 标签页激活时自动加载图谱
2. ✅ 搜索功能正常
3. ✅ 设置模态框可以调整参数
4. ✅ 详情面板显示在合适位置
5. ✅ 非 LightRAG 类型知识库显示不可用提示

---

### 3. KnowledgeGraphTool.vue (智能体工具结果显示)

**文件路径**: `web/src/components/ToolCallingResult/tools/KnowledgeGraphTool.vue`

**使用的 GraphCanvas Props**:
- `graph-data`: 从智能体返回的三元组数据转换而来

**使用的 Slots**:
- `#top` - 刷新按钮

**功能集成**:
- ✅ 数据解析 - 解析智能体返回的 triples 格式数据
- ✅ 动态渲染 - 工具调用结果更新时自动刷新图谱
- ✅ 手动刷新 - 提供刷新按钮重新渲染
- ✅ 可见性检测 - 检测容器是否可见后再渲染

**兼容性分析**:
- ✅ Props 接口兼容
- ✅ refreshGraph 方法可用
- ✅ 小数据集渲染 - 通常 < 50 节点
- ✅ 自动重试机制 - 通过定时器和可见性检测确保渲染

**预期行为验证**:
1. ✅ 工具调用完成后自动显示图谱
2. ✅ 显示节点和关系数量统计
3. ✅ 刷新按钮正常工作
4. ✅ 图谱容器高度固定为 360px
5. ✅ 数据格式转换正确（triples → nodes/edges）

**数据转换示例**:
```javascript
// 输入: { triples: [["实体A", "关系", "实体B"]] }
// 输出: {
//   nodes: [
//     { id: "实体A", name: "实体A" },
//     { id: "实体B", name: "实体B" }
//   ],
//   edges: [
//     { source_id: "实体A", target_id: "实体B", type: "关系", id: "edge_0" }
//   ]
// }
```

---

## 功能对等性验证

### G6 功能 → 3d-force-graph 映射

| G6 功能 | 3d-force-graph 等效 | 状态 |
|---------|-------------------|------|
| 节点点击 | `onNodeClick` | ✅ 已实现 |
| 边点击 | `onLinkClick` | ✅ 已实现 |
| 画布点击 | `onBackgroundClick` | ✅ 已实现 |
| 节点拖拽 | `enableNodeDrag(true)` | ✅ 已实现 |
| 缩放画布 | 内置鼠标滚轮缩放 | ✅ 已实现 |
| 拖拽画布 | 内置右键拖拽 | ✅ 已实现 |
| 悬停激活 | 内置悬停高亮 | ✅ 已实现 |
| 关键词高亮 | `nodeColor` 访问器 | ✅ 已实现 |
| 焦点模式 | `nodeVisibility/linkVisibility` | ✅ 已实现 |
| 适应视图 | `cameraPosition` | ✅ 已实现 |
| 主题切换 | CSS 变量 + watch | ✅ 已实现 |
| 统计面板 | Slot 覆盖层 | ✅ 已实现 |

---

## 视觉回归测试

### 布局对比

**G6 (2D)**:
- Force-directed 力导向布局
- 节点在 2D 平面上分布
- 固定视角，仅支持平移和缩放

**3d-force-graph (3D)**:
- d3-force-3d 3D 力导向布局
- 节点在 3D 空间中分布
- 支持旋转、平移、缩放
- 深度感知（节点有前后层次）

### 样式对比

| 元素 | G6 样式 | 3d-force-graph 样式 | 匹配度 |
|------|---------|-------------------|--------|
| 节点颜色 | 调色板 (10 色) | 单色 (CSS 变量) | ⚠️ 简化 |
| 节点大小 | 基于度数 (15-50) | 基于度数 (15-50) | ✅ 一致 |
| 节点形状 | 圆形 | 球体 (3D) | ✅ 等效 |
| 边颜色 | CSS 变量 | CSS 变量 | ✅ 一致 |
| 边箭头 | 内置 | 定向箭头 | ✅ 一致 |
| 边标签 | 背景填充 | 悬停显示 | ⚠️ 简化 |
| 标签字体 | CSS 继承 | Canvas 渲染 | ✅ 相似 |

**注意**: 节点颜色从多彩调色板简化为单色 + 高亮色，这是为了 3D 视觉一致性。如需恢复多色，可以在 `nodeColor` 访问器中添加哈希函数。

---

## API 兼容性验证

### Props 接口

所有 props 保持不变，无需修改消费者代码：

```javascript
// ✅ 完全兼容
<GraphCanvas
  :graph-data="{ nodes, edges }"
  :graph-info="{ node_count, edge_count }"
  :label-field="'name'"
  :auto-fit="true"
  :auto-resize="true"
  :layout-options="{}"
  :node-style-options="{}"
  :edge-style-options="{}"
  :enable-focus-neighbor="true"
  :size-by-degree="true"
  :highlight-keywords="['keyword']"
  @ready="onReady"
  @data-rendered="onRendered"
  @node-click="onNodeClick"
  @edge-click="onEdgeClick"
  @canvas-click="onCanvasClick"
/>
```

### Events 接口

事件有效载荷格式保持一致：

```javascript
// node-click 事件
{
  id: "node-123",
  data: {
    label: "节点名称",
    degree: 5,
    original: { /* 原始数据 */ }
  }
}

// edge-click 事件
{
  id: "edge-456",
  source: "node-a",
  target: "node-b",
  data: {
    label: "关系类型",
    original: { /* 原始数据 */ }
  }
}
```

### 暴露方法

所有方法签名保持一致：

```javascript
const graphRef = ref(null)

// ✅ 所有方法可用
graphRef.value.refreshGraph()      // 重新渲染
graphRef.value.fitView()           // 适应视图
graphRef.value.fitCenter()         // 居中
graphRef.value.getInstance()       // 获取实例
graphRef.value.focusNode(id)       // 聚焦节点
graphRef.value.clearFocus()        // 清除聚焦
graphRef.value.setData(data)       // 设置数据
graphRef.value.applyHighlightKeywords()  // 应用高亮
graphRef.value.clearHighlights()   // 清除高亮
```

---

## 已知差异和限制

### 1. 节点颜色 (设计决策)

**差异**: G6 使用 10 色调色板，3d-force-graph 使用单色 + 高亮

**原因**: 3D 环境中过多颜色会造成视觉混乱

**解决方案**: 如需恢复多色，可以修改 `nodeColor` 访问器：

```javascript
graph.nodeColor(node => {
  // 高亮节点
  if (isHighlighted(node)) return '#ff4d4f'

  // 基于标签哈希选择颜色
  const colors = ['#60a5fa', '#34d399', '#f59e0b', '#f472b6', ...]
  const hash = node.name.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0)
  return colors[hash % colors.length]
})
```

### 2. 边标签显示

**差异**: G6 始终显示边标签（带背景），3d-force-graph 悬停显示

**原因**: 3D 空间中大量标签会遮挡视图

**当前实现**: 标签在悬停时显示

**替代方案**: 如需始终显示，设置 `linkLabel` 并调整相机距离

### 3. 布局预热时间

**差异**: 3d-force-graph 需要 1.5 秒预热时间

**原因**: 3D 物理模拟需要更多计算

**当前实现**: 显示加载动画，1500ms 后隐藏

**优化**: 可以调整 `warmupTicks` 和 `cooldownTicks` 参数

---

## WebGL 兼容性

### 浏览器支持

**支持 WebGL 的浏览器**:
- ✅ Chrome 56+
- ✅ Firefox 52+
- ✅ Safari 12+
- ✅ Edge 79+

**不支持 WebGL**:
- ❌ IE 11 及以下
- ❌ 旧版 Android 浏览器 (< 5.0)

**降级处理**:
当检测到不支持 WebGL 时，显示友好错误消息：

```html
<a-alert
  type="warning"
  message="您的浏览器不支持 WebGL，无法渲染 3D 图谱"
  show-icon
/>
```

---

## 结论

### 测试结果总结

✅ **所有消费者组件兼容性测试通过**:
- GraphView.vue: 完全兼容，无需修改
- KnowledgeGraphSection.vue: 完全兼容，无需修改
- KnowledgeGraphTool.vue: 完全兼容，无需修改

✅ **功能对等性验证通过**:
- 所有 G6 功能都有 3D 等效实现
- Props/Events/Methods 接口保持 100% 兼容

⚠️ **已知差异**:
- 节点颜色简化为单色（可选恢复多色）
- 边标签悬停显示（符合 3D 最佳实践）
- 布局预热时间 1.5 秒（可接受）

### 下一步

继续进行 **任务 6.2: 性能测试**，使用大型数据集验证性能提升。

---

## 附录

### 测试环境

- Docker 容器: web-dev (Up 20 hours)
- 后端服务: api-dev (Up 3 hours, healthy)
- Vite HMR: 正常工作
- 浏览器: Chrome/Firefox/Safari

### 测试数据

测试使用了以下数据集：
- 小型: < 50 节点 (KnowledgeGraphTool)
- 中型: 100-500 节点 (GraphView 示例数据)
- 大型: 将在任务 6.2 中测试 (1000+ 节点)
