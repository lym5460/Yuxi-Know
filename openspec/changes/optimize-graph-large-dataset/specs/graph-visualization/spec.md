# Capability: Graph Visualization

知识图谱可视化能力规范

## ADDED Requirements

### Requirement: Performance-Adaptive Rendering

系统 SHALL 根据数据集规模自动调整渲染参数以优化性能。

#### Scenario: Small Dataset Rendering
- **WHEN** 图谱数据包含少于 500 个节点
- **THEN** 系统应使用高质量渲染配置
- **AND** 所有节点标签应始终可见
- **AND** 渲染应在 1 秒内完成

#### Scenario: Medium Dataset Rendering
- **WHEN** 图谱数据包含 500 到 1000 个节点
- **THEN** 系统应使用高质量渲染配置
- **AND** 所有节点标签应始终可见
- **AND** 渲染应在 2 秒内完成
- **AND** 交互帧率应保持在 50 FPS 以上

#### Scenario: Large Dataset Rendering
- **WHEN** 图谱数据包含 1000 到 2000 个节点
- **THEN** 系统应使用性能优化配置
- **AND** 节点标签应默认隐藏
- **AND** 悬停节点时应通过 tooltip 显示节点信息
- **AND** 渲染应在 3 秒内完成
- **AND** 交互帧率应保持在 40 FPS 以上

#### Scenario: Extra Large Dataset Rendering
- **WHEN** 图谱数据包含超过 2000 个节点
- **THEN** 系统应使用最大性能优化配置
- **AND** 节点标签应默认隐藏
- **AND** 节点几何复杂度应降低
- **AND** 渲染应在 5 秒内完成
- **AND** 交互帧率应保持在 30 FPS 以上

---

### Requirement: Performance Feedback

系统 SHALL 向用户提供性能相关的反馈信息。

#### Scenario: Large Dataset Warning
- **WHEN** 加载超过 1000 个节点的图谱
- **THEN** 系统应显示性能提示信息
- **AND** 提示应说明已启用性能优化模式
- **AND** 提示应解释标签显示策略
- **AND** 用户应能关闭该提示

#### Scenario: Rendering Progress Indication
- **WHEN** 图谱正在渲染
- **THEN** 系统应显示加载指示器
- **AND** 加载指示器应显示节点数量
- **AND** 大数据集（> 1000 节点）应显示额外的等待提示

#### Scenario: Performance Metrics Logging
- **WHEN** 图谱渲染完成
- **THEN** 系统应记录渲染时间到控制台
- **AND** 系统应触发 `data-rendered` 事件
- **AND** 事件应包含性能指标（renderTime, nodeCount, linkCount）

---

### Requirement: Optimized Force Layout Parameters

系统 SHALL 根据数据规模动态调整力导向布局参数以加快收敛速度。

#### Scenario: Small Dataset Layout
- **WHEN** 图谱包含少于 1000 个节点
- **THEN** 使用标准力参数配置
- **AND** charge strength 应为 -400
- **AND** link distance 应为 100
- **AND** warmupTicks 应为 100

#### Scenario: Large Dataset Layout
- **WHEN** 图谱包含超过 1000 个节点
- **THEN** 使用优化的力参数配置
- **AND** charge strength 应减弱至 -200
- **AND** link distance 应缩短至 60
- **AND** warmupTicks 应减少至 50 或更少
- **AND** 布局应在合理时间内收敛（< 5 秒）

---

### Requirement: Clean Dependency Management

系统 SHALL 仅包含实际使用的依赖包，移除冗余依赖以减小打包体积。

#### Scenario: Sigma Dependencies Removed
- **WHEN** 构建前端应用
- **THEN** package.json 不应包含 sigma 相关依赖
- **AND** package.json 不应包含 graphology 相关依赖
- **AND** 构建应成功完成无错误
- **AND** 应用功能应保持完整

#### Scenario: Reduced Bundle Size
- **WHEN** 构建生产版本
- **THEN** vendor bundle 体积应比移除前减小至少 400KB
- **AND** 应用仍应正常运行
- **AND** 所有图谱功能应保持可用

---

## MODIFIED Requirements

### Requirement: Node Label Display Strategy

节点标签的显示策略 SHALL 根据数据集规模动态调整。

#### Scenario: Always-On Labels for Small Datasets
- **WHEN** 图谱包含少于 1000 个节点
- **THEN** 所有节点标签应始终可见
- **AND** 标签应使用 Three.js SpriteText 渲染在节点上方
- **AND** 标签应有背景色和边框以提高可读性

#### Scenario: Hover-Only Labels for Large Datasets
- **WHEN** 图谱包含超过 1000 个节点
- **THEN** 节点标签应默认隐藏
- **AND** 悬停节点时应显示 tooltip
- **AND** tooltip 应包含节点名称和其他相关信息
- **AND** 移开鼠标后 tooltip 应隐藏

---

### Requirement: Graph Rendering Configuration

图谱渲染配置 SHALL 支持根据数据规模自适应调整。

#### Scenario: Adaptive Node Resolution
- **WHEN** 图谱包含少于 1000 个节点
- **THEN** nodeResolution 应为 16（高质量球体）

- **WHEN** 图谱包含 1000 到 2000 个节点
- **THEN** nodeResolution 应为 12（中等质量）

- **WHEN** 图谱包含超过 2000 个节点
- **THEN** nodeResolution 应为 8（低质量，高性能）

#### Scenario: Adaptive Link Opacity
- **WHEN** 图谱包含少于 1000 个节点
- **THEN** link opacity 应为 0.4 到 0.5

- **WHEN** 图谱包含超过 1000 个节点
- **THEN** link opacity 应降低至 0.2 到 0.3
- **AND** 以减少视觉混乱

---

## REMOVED Requirements

（无）
