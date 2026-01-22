# 能力：3D 图谱可视化

## 概述
本规范定义了使用 3d-force-graph 库进行 3D 知识图谱可视化的需求，替换现有的 @antv/g6 实现，以支持大型图（1000+ 节点）的高性能渲染。

## ADDED Requirements

### Requirement: 3D WebGL 渲染引擎
The system SHALL use 3d-force-graph 库和 ThreeJS/WebGL 后端进行图谱可视化。

#### Scenario:初始化 3D 图实例
**前提** 存在一个有效的 DOM 容器元素
**当** GraphCanvas 组件挂载时
**那么** 创建一个带有 WebGL 渲染器的 3d-force-graph 实例
**并且** 实例被附加到容器元素上
**并且** 图谱准备好接受数据

#### Scenario:处理 WebGL 不可用
**前提** 用户的浏览器不支持 WebGL
**当** GraphCanvas 组件尝试初始化时
**那么** 显示警告消息
**并且** 消息内容为"您的浏览器不支持 WebGL，无法渲染 3D 图谱"
**并且** 不抛出 JavaScript 错误

---

### 需求：数据格式转换
The system SHALL transform后端图数据格式转换为 3d-force-graph 格式。

#### Scenario:转换节点从 G6 到 3d-force-graph 格式
**前提** 后端返回格式为 `{id, name, ...}` 的节点
**当** formatData() 函数处理数据时
**那么** 每个节点被转换为包含以下内容：
- `id`（字符串）：唯一标识符
- `name`（字符串）：来自 labelField prop 的显示标签
- `degree`（数字）：连接边的数量
- `val`（数字）：如果 sizeByDegree=true，基于度数的视觉大小
- `original`（对象）：对原始节点数据的引用

#### Scenario:转换边为连接
**前提** 后端返回格式为 `{source_id, target_id, type}` 的边
**当** formatData() 函数处理数据时
**那么** 每条边被转换为包含以下内容的连接：
- `source`（字符串）：源节点 id
- `target`（字符串）：目标节点 id
- `label`（字符串）：边类型/标签
- `original`（对象）：对原始边数据的引用

#### Scenario:计算节点度数
**前提** 一个包含节点和边的图
**当** formatData() 计算度数时
**那么** 每个节点的度数等于该节点作为源或目标的边的数量
**并且** 孤立节点的度数为 0

---

### 需求：力导向布局
The system SHALL use d3-force-3d 物理模拟进行节点定位。

#### Scenario:配置力模拟参数
**前提** 一个 3d-force-graph 实例
**当** 应用布局配置时
**那么** 配置以下力：
- 电荷力：strength=-400，distanceMax=600（排斥）
- 连接力：distance=100，strength=0.8（边约束）
- 中心力：将图谱居中于原点
- 碰撞力：radius=40，strength=0.8（防止重叠）
**并且** alphaDecay=0.1，velocityDecay=0.6
**并且** warmupTicks=100，cooldownTicks=150

#### Scenario:布局稳定
**前提** 加载图数据
**当** 力模拟运行时
**那么** 布局在 3 秒内稳定
**并且** 节点均匀分布，无聚集
**并且** 无节点重叠（碰撞检测激活）

---

### 需求：节点视觉样式
The system SHALL transform节点渲染为基于节点属性动态样式的 3D 球体。

#### Scenario:根据度数渲染节点大小
**前提** sizeByDegree prop 为 true
**并且** 一个节点度数为 D
**当** 节点被渲染时
**那么** 节点大小 = min(15 + D * 5, 50)
**并且** 节点被渲染为具有 16 段的球体

#### Scenario:固定大小渲染节点
**前提** sizeByDegree prop 为 false
**当** 节点被渲染时
**那么** 所有节点具有统一大小 = 24

#### Scenario:应用主题感知节点颜色
**前提** 主题存储指示暗黑模式
**当** 渲染节点时
**那么** 节点颜色从 CSS 变量 `--gray-700` 提取
**并且** 主题变化时颜色动态更新
**并且** 主题切换时不发生完全重新渲染

#### Scenario:显示节点标签
**前提** 一个名为"实体 A"的节点
**当** 渲染节点时
**那么** 显示标签"实体 A"
**并且** 标签在悬停时可见或根据相机距离始终可见

#### Scenario:节点不透明度和材质
**前提** 任何节点
**当** 渲染时
**那么** 节点不透明度 = 0.9
**并且** 材质 = MeshLambertMaterial（响应光照）

---

### 需求：连接（边）视觉样式
The system SHALL transform连接渲染为节点之间的定向连接。

#### Scenario:带箭头渲染连接
**前提** 两个连接的节点
**当** 渲染连接时
**那么** 从源到目标绘制一条线
**并且** 定向箭头出现在目标端
**并且** 箭头长度 = 3.5 单位
**并且** 箭头位置 = 1.0（在目标节点处）

#### Scenario:应用主题感知连接颜色
**前提** 当前主题
**当** 渲染连接时
**那么** 连接颜色从 CSS 变量 `--gray-400` 提取
**并且** 主题变化时颜色更新

#### Scenario:配置连接外观
**前提** 任何连接
**当** 渲染时
**那么** 连接宽度 = 1.2
**并且** 连接不透明度 = 0.8
**并且** 连接具有轻微曲线 = 0.1（用于重叠边）

#### Scenario:显示连接标签
**前提** 一个类型为"RELATED_TO"的连接
**当** 渲染连接时
**那么** 在悬停时或始终显示标签"RELATED_TO"

---

### 需求：节点交互事件
The system SHALL emit events when用户与节点交互时发出事件。

#### Scenario:点击节点
**前提** 一个包含节点的已渲染图
**当** 用户点击 id 为"node-123"的节点时
**那么** 发出 `node-click` 事件
**并且** 事件有效载荷包含：
```javascript
{
  id: "node-123",
  data: {
    label: "节点名称",
    degree: 5,
    original: { /* 原始节点数据 */ }
  }
}
```

#### Scenario:悬停在节点上
**前提** 一个已渲染的图
**当** 用户悬停在节点上时
**那么** 节点被视觉高亮（亮度增加或发光）
**并且** 节点标签变得更突出

---

### 需求：连接交互事件
The system SHALL emit events when用户与连接交互时发出事件。

#### Scenario:点击连接
**前提** 一个包含连接的已渲染图
**当** 用户点击节点 A 和节点 B 之间的连接时
**那么** 发出 `edge-click` 事件
**并且** 事件有效载荷包含：
```javascript
{
  id: "edge-id",
  source: "node-a-id",
  target: "node-b-id",
  data: {
    label: "RELATED_TO",
    original: { /* 原始边数据 */ }
  }
}
```

---

### 需求：画布交互事件
The system SHALL emit events when用户与空白空间交互时发出事件。

#### Scenario:点击空白空间
**前提** 一个已渲染的图
**当** 用户点击 3D 画布背景（不在节点或连接上）时
**那么** 发出 `canvas-click` 事件
**并且** 有效载荷中不包含节点或连接数据

---

### 需求：相机控制
The system SHALL provide用于导航的直观 3D 相机控制。

#### Scenario:用鼠标拖拽旋转相机
**前提** 一个已渲染的图
**当** 用户左键点击并拖拽鼠标时
**那么** 相机围绕图中心旋转
**并且** 旋转平滑跟随鼠标移动

#### Scenario:用鼠标滚轮缩放相机
**前提** 一个已渲染的图
**当** 用户滚动鼠标滚轮时
**那么** 相机放大（向上滚动）或缩小（向下滚动）
**并且** 缩放以鼠标光标位置为中心

#### Scenario:用右键拖拽平移相机
**前提** 一个已渲染的图
**当** 用户右键点击并拖拽鼠标时
**那么** 相机沿拖拽方向平移
**并且** 图中心在 3D 空间中保持固定

#### Scenario:在 3D 空间中拖拽节点
**前提** enableNodeDrag 为 true
**当** 用户点击并拖拽节点时
**那么** 节点在 3D 空间中跟随光标移动
**并且** 连接的连接相应伸展
**并且** 力模拟更新以适应新位置

---

### 需求：关键词搜索高亮
The system SHALL highlight匹配搜索关键词的节点。

#### Scenario:按关键词高亮节点
**前提** 一个包含节点"Alice"、"Bob"、"Albert"的图
**并且** highlightKeywords prop = ["ali"]
**当** 应用高亮时
**那么** 节点"Alice"和"Albert"颜色变为 `#ff4d4f`（高亮红色）
**并且** 其他节点保留默认颜色
**并且** 匹配不区分大小写

#### Scenario:清除高亮
**前提** 存在高亮节点
**当** highlightKeywords prop 变为空数组时
**那么** 所有节点颜色恢复为默认主题颜色
**并且** 无节点保持高亮

#### Scenario:关键词变化时更新高亮
**前提** 当前高亮节点
**当** highlightKeywords prop 更改为新关键词时
**那么** 清除之前的高亮
**并且** 高亮新匹配的节点
**并且** 过渡平滑（< 50ms 延迟）

---

### 需求：焦点模式（邻居可见性）
The system SHALL show only选定节点及其直接邻居。

#### Scenario:聚焦节点和邻居
**前提** 一个图，其中节点 A 连接到节点 B、C、D
**并且** 节点 A 未连接到节点 E、F
**当** 调用 focusNode("A") 时
**那么** 节点 A、B、C、D 保持可见
**并且** 节点 E、F 被隐藏
**并且** 仅连接 A 到 B/C/D 的连接保持可见
**并且** 所有其他连接被隐藏

#### Scenario:清除焦点模式
**前提** 焦点模式激活，可见节点有限
**当** 调用 clearFocus() 时
**那么** 所有节点再次可见
**并且** 所有连接再次可见
**并且** 图返回完整视图

#### Scenario:通过 prop 禁用焦点
**前提** enableFocusNeighbor prop 为 false
**当** 调用 focusNode() 时
**那么** 不发生可见性变化
**并且** 方法提前返回，无错误

---

### 需求：适应视图控制
The system SHALL provide方法重置相机位置。

#### Scenario:适应视图以显示所有节点
**前提** 一个节点分布在 3D 空间的图
**当** 调用 fitView() 时
**那么** 相机动画到位置 (0, 0, 300)
**并且** 相机看向图中心 (0, 0, 0)
**并且** 动画持续时间 = 1000ms
**并且** 所有节点在视口内可见

#### Scenario:以更短动画适应中心
**前提** 任何图状态
**当** 调用 fitCenter() 时
**那么** 相机动画到位置 (0, 0, 300)
**并且** 动画持续时间 = 500ms
**并且** 相机居中于原点

---

### 需求：动态主题支持
The system SHALL respond to主题变化而无需完全重新渲染。

#### Scenario:从明亮切换到暗黑主题
**前提** 图以明亮主题渲染
**并且** 节点颜色 = 明亮主题 `--gray-700`
**当** themeStore.isDark 更改为 true 时
**那么** 节点颜色更新为暗黑主题 `--gray-700`
**并且** 连接颜色更新为暗黑主题 `--gray-400`
**并且** 图不销毁并重新初始化
**并且** 更新在 100ms 内完成

#### Scenario:主题切换期间保留高亮节点
**前提** 某些节点通过关键词搜索高亮
**当** 主题变化时
**那么** 高亮节点保持高亮颜色 `#ff4d4f`
**并且** 非高亮节点采用新主题颜色

---

### 需求：容器调整大小处理
The system SHALL emit events when容器大小变化时调整图尺寸。

#### Scenario:浏览器窗口调整大小
**前提** 图容器为 800x600px
**当** 浏览器窗口调整大小为 1200x900px 时
**那么** 图画布调整大小为 1200x900px
**并且** 3D 场景保持纵横比
**并且** 不发生扭曲
**并且** 调整大小在 100ms 内发生

#### Scenario:ResizeObserver 降级
**前提** ResizeObserver 不可用（旧浏览器）
**当** 组件挂载时
**那么** 图仍以初始大小渲染
**并且** 不发生控制台错误
**并且** 调整大小可能需要手动刷新

---

### 需求：组件生命周期管理
The system SHALL properly初始化和清理资源。

#### Scenario:延迟容器大小挂载
**前提** 容器元素最初大小为 0x0
**当** 组件挂载时
**那么** 初始化最多重试 5 次，延迟 200ms
**并且** 一旦容器具有非零大小，图成功初始化

#### Scenario:卸载和清理
**前提** 一个已渲染的图实例
**当** 组件卸载时
**那么** 通过 `_destructor()` 销毁 3d-force-graph 实例
**并且** ResizeObserver 断开连接
**并且** 移除事件监听器
**并且** 不发生内存泄漏

#### Scenario:刷新图
**前提** 一个已渲染的图
**当** 调用 refreshGraph() 时
**那么** 销毁当前实例
**并且** 清除容器
**并且** 300ms 延迟后创建新实例
**并且** 使用当前 props 重新渲染数据

---

### 需求：加载状态
The system SHALL emit events when图初始化期间指示加载。

#### Scenario:预热期间显示加载
**前提** 正在加载图数据
**当** 力模拟正在预热（warmupTicks 进行中）时
**那么** 显示加载旋转器覆盖层
**并且** 图画布隐藏在覆盖层后面

#### Scenario:准备就绪时隐藏加载
**前提** 加载旋转器可见
**当** 力模拟引擎停止（布局稳定）时
**那么** 加载旋转器淡出
**并且** 图画布完全可见
**并且** 发出 `data-rendered` 事件

---

### 需求：性能优化
The system SHALL efficiently渲染大型图。

#### Scenario:渲染 1000 节点图
**前提** 一个包含 1000 个节点和 1500 个连接的数据集
**当** 渲染图时
**那么** 初始渲染在 3 秒内完成
**并且** 渲染期间 UI 保持响应
**并且** 布局模拟期间帧率保持在 30 FPS 以上

#### Scenario:交互期间保持 60 FPS
**前提** 一个已渲染的 1000 节点图
**当** 用户旋转、缩放或平移相机时
**那么** 帧率保持在 60 FPS 或以上
**并且** 交互感觉平滑无延迟

#### Scenario:远距离高效标签渲染
**前提** 相机缩小（距离 > 500 单位）
**当** 渲染节点时
**那么** 隐藏节点标签以提高性能
**并且** 相机放大时标签重新出现（距离 < 500）

---

### 需求：API 兼容性
The system SHALL maintain与现有消费者的向后兼容性。

#### Scenario:Props 接口不变
**前提** 一个消费者组件（例如 GraphView.vue）
**当** 它向 GraphCanvas 传递 props 时
**那么** 接受所有现有 props：
- graphData（对象）
- graphInfo（对象）
- labelField（字符串）
- autoFit（布尔值）
- autoResize（布尔值）
- layoutOptions（对象）
- nodeStyleOptions（对象）
- edgeStyleOptions（对象）
- enableFocusNeighbor（布尔值）
- sizeByDegree（布尔值）
- highlightKeywords（数组）

#### Scenario:Events 接口不变
**前提** 一个带有事件处理器的消费者组件
**当** GraphCanvas 发出事件时
**那么** 以不变的有效载荷发出以下事件：
- `ready`（graphInstance）
- `data-rendered`（）
- `node-click`（nodeData）
- `edge-click`（edgeData）
- `canvas-click`（）

#### Scenario:暴露的方法不变
**前提** 一个带有 GraphCanvas ref 的消费者组件
**当** 它调用暴露的方法时
**那么** 以下方法与 G6 版本工作方式相同：
- `refreshGraph()`
- `fitView()`
- `fitCenter()`
- `getInstance()`
- `focusNode(id)`
- `clearFocus()`
- `setData(data)`
- `applyHighlightKeywords()`
- `clearHighlights()`

---

### 需求：统计覆盖层兼容性
The system SHALL preserve统计覆盖层显示。

#### Scenario:显示节点和边计数
**前提** graphInfo prop = `{ node_count: 1500, edge_count: 2200 }`
**并且** 当前 graphData 有 100 个节点和 150 条边（采样）
**当** 渲染图时
**那么** 统计面板显示：
- "节点 100 / 1500"
- "边 150 / 2200"
**并且** 面板位于左下角
**并且** 面板具有背景模糊效果

---

## MODIFIED Requirements

*无修改的需求 - 这是完全替换*

---

## REMOVED Requirements

### 需求：G6 Canvas 渲染（已移除）
~~The system SHALL use @antv/g6 进行基于 2D canvas 的图谱可视化~~

**原因**：为了性能，替换为 3D WebGL 渲染

### 需求：G6 行为系统（已移除）
~~系统应当配置 G6 行为：drag-element、zoom-canvas、drag-canvas、hover-activate、click-select~~

**原因**：3d-force-graph 提供内置相机控制和交互

### 需求：G6 状态管理（已移除）
~~系统应当管理节点状态：selected、active、inactive、hidden、focus、highlighted~~

**原因**：3d-force-graph 使用可见性和颜色访问器代替状态系统
