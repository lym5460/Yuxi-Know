# Requirements Document

## Introduction

本文档定义了基于 API Key 的第三方认证机制的需求。该功能允许系统管理员创建和管理 API Key，使第三方应用能够通过 API Key 安全地访问知识库查询等开放接口。

## Glossary

- **API_Key_Manager**: 负责 API Key 的创建、存储、验证和管理的系统组件
- **Open_API_Gateway**: 处理第三方 API 请求的网关组件，负责验证 API Key 并路由请求
- **API_Key**: 用于第三方认证的唯一密钥字符串，格式为 `yk_` 前缀加随机字符串
- **Third_Party_Client**: 使用 API Key 访问系统开放接口的外部应用程序
- **Rate_Limiter**: 限制 API 调用频率的组件，防止滥用

## Requirements

### Requirement 1: API Key 创建

**User Story:** As a 系统管理员, I want to 创建新的 API Key, so that 第三方应用可以获得访问系统的凭证。

#### Acceptance Criteria

1. WHEN 管理员请求创建 API Key 并提供名称和描述 THEN THE API_Key_Manager SHALL 生成一个唯一的 API Key 并存储到数据库
2. THE API_Key_Manager SHALL 生成格式为 `yk_` 前缀加 32 位随机字符的 API Key
3. WHEN API Key 创建成功 THEN THE API_Key_Manager SHALL 仅在创建时返回完整的 API Key 明文一次
4. THE API_Key_Manager SHALL 仅存储 API Key 的哈希值，不存储明文
5. WHEN 创建 API Key 时 THEN THE API_Key_Manager SHALL 记录创建者用户ID、创建时间和过期时间

### Requirement 2: API Key 列表查看

**User Story:** As a 系统管理员, I want to 查看所有 API Key 列表, so that 我可以了解当前系统中存在哪些 API Key。

#### Acceptance Criteria

1. WHEN 管理员请求 API Key 列表 THEN THE API_Key_Manager SHALL 返回所有 API Key 的元数据（不包含密钥明文）
2. THE API_Key_Manager SHALL 在列表中显示 API Key 的名称、描述、创建时间、过期时间、状态和最后使用时间
3. THE API_Key_Manager SHALL 仅显示 API Key 的前缀部分（如 `yk_xxxx...`）用于识别

### Requirement 3: API Key 删除

**User Story:** As a 系统管理员, I want to 删除不再需要的 API Key, so that 我可以撤销第三方的访问权限。

#### Acceptance Criteria

1. WHEN 管理员请求删除指定的 API Key THEN THE API_Key_Manager SHALL 从数据库中永久删除该 API Key
2. WHEN API Key 被删除后 THEN THE Open_API_Gateway SHALL 立即拒绝使用该 API Key 的所有请求

### Requirement 4: API Key 启用/禁用

**User Story:** As a 系统管理员, I want to 临时禁用或重新启用 API Key, so that 我可以在不删除的情况下控制访问权限。

#### Acceptance Criteria

1. WHEN 管理员禁用一个 API Key THEN THE API_Key_Manager SHALL 将该 API Key 状态设置为禁用
2. WHILE API Key 处于禁用状态 THEN THE Open_API_Gateway SHALL 拒绝使用该 API Key 的所有请求
3. WHEN 管理员启用一个已禁用的 API Key THEN THE API_Key_Manager SHALL 将该 API Key 状态恢复为启用

### Requirement 5: API Key 认证验证

**User Story:** As a 第三方开发者, I want to 使用 API Key 访问开放接口, so that 我的应用可以查询知识库数据。

#### Acceptance Criteria

1. WHEN Third_Party_Client 发送请求时在 Authorization 头中携带 `Bearer {api_key}` THEN THE Open_API_Gateway SHALL 验证该 API Key 的有效性
2. WHEN API Key 验证通过且状态为启用 THEN THE Open_API_Gateway SHALL 允许请求继续处理
3. IF API Key 不存在或无效 THEN THE Open_API_Gateway SHALL 返回 401 Unauthorized 错误
4. IF API Key 已过期 THEN THE Open_API_Gateway SHALL 返回 401 Unauthorized 错误并说明密钥已过期
5. IF API Key 已禁用 THEN THE Open_API_Gateway SHALL 返回 403 Forbidden 错误
6. WHEN API Key 验证成功 THEN THE API_Key_Manager SHALL 更新该 API Key 的最后使用时间

### Requirement 6: 开放 API 接口框架

**User Story:** As a 开发者, I want to 系统具有可扩展的开放 API 框架, so that 未来可以方便地添加各类开放接口供第三方使用。

#### Acceptance Criteria

1. THE Open_API_Gateway SHALL 使用统一的路由前缀 `/api/v1/open/` 来组织所有开放接口
2. THE Open_API_Gateway SHALL 通过依赖注入统一处理 API Key 认证和权限验证
3. THE Open_API_Gateway SHALL 提供 OpenAPI/Swagger 文档，方便第三方开发者了解接口规范
4. WHEN 添加新的开放接口时 THE 开发者 SHALL 只需创建新的路由并指定所需权限范围

### Requirement 6.1: API Key 权限范围控制

**User Story:** As a 系统管理员, I want to 为每个 API Key 设置可访问的接口范围, so that 我可以精细控制第三方的访问权限。

#### Acceptance Criteria

1. WHEN 创建或编辑 API Key 时 THEN THE API_Key_Manager SHALL 允许管理员选择该 API Key 可访问的权限范围
2. THE API_Key_Manager SHALL 使用 JSON 数组存储权限范围，支持动态扩展
3. IF Third_Party_Client 请求的接口不在 API Key 的权限范围内 THEN THE Open_API_Gateway SHALL 返回 403 Forbidden 错误
4. THE 前端界面 SHALL 在创建/编辑 API Key 时提供权限范围的多选控件
5. THE 系统 SHALL 预定义以下初始权限范围：`knowledge:read`（知识库查询）、`knowledge:list`（知识库列表）

### Requirement 6.2: 示例开放接口 - 知识库

**User Story:** As a 第三方开发者, I want to 通过 API 查询知识库, so that 我可以在我的应用中集成知识库搜索功能。

#### Acceptance Criteria

1. WHEN Third_Party_Client 发送知识库查询请求且具有 `knowledge:read` 权限 THEN THE Open_API_Gateway SHALL 执行查询
2. THE Open_API_Gateway SHALL 支持指定知识库ID、查询文本和返回数量参数
3. WHEN Third_Party_Client 请求知识库列表且具有 `knowledge:list` 权限 THEN THE Open_API_Gateway SHALL 返回可用知识库信息
4. IF 指定的知识库不存在 THEN THE Open_API_Gateway SHALL 返回 404 Not Found 错误

### Requirement 7: API 调用频率限制

**User Story:** As a 系统管理员, I want to 限制 API 调用频率, so that 系统资源不会被滥用。

#### Acceptance Criteria

1. THE Rate_Limiter SHALL 对每个 API Key 实施每分钟最大请求数限制
2. IF API Key 超过频率限制 THEN THE Rate_Limiter SHALL 返回 429 Too Many Requests 错误
3. WHEN 返回 429 错误时 THEN THE Rate_Limiter SHALL 在响应头中包含 Retry-After 字段

### Requirement 8: 前端 API Key 管理界面

**User Story:** As a 系统管理员, I want to 通过图形界面管理 API Key, so that 我可以方便地进行 API Key 的增删改查操作。

#### Acceptance Criteria

1. THE 前端界面 SHALL 显示 API Key 列表，包含名称、状态、创建时间和最后使用时间
2. THE 前端界面 SHALL 提供创建新 API Key 的表单，包含名称、描述和过期时间字段
3. WHEN 新 API Key 创建成功 THEN THE 前端界面 SHALL 显示完整的 API Key 明文并提示用户保存
4. THE 前端界面 SHALL 提供一键复制 API Key 的功能
5. THE 前端界面 SHALL 提供启用/禁用 API Key 的开关控件
6. THE 前端界面 SHALL 提供删除 API Key 的功能，并在删除前显示确认对话框
