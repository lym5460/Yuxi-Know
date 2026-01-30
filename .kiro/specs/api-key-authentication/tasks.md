# Implementation Plan: API Key Authentication

## Overview

基于 API Key 的第三方认证机制实现计划。按照模块化原则，将实现分为数据层、服务层、路由层和前端层，每个模块职责单一。

## Tasks

- [x] 1. 数据模型层实现
  - [x] 1.1 在 `src/storage/postgres/models_business.py` 中添加 APIKey 模型
    - 定义 APIKey 表结构：id, name, description, key_prefix, key_hash, scopes, is_active, expires_at, last_used_at, created_by, created_at, updated_at
    - 实现 to_dict() 方法
    - _Requirements: 1.1, 1.2, 1.4, 1.5_

- [x] 2. API Key 服务层实现
  - [x] 2.1 创建 `src/services/apikey_service.py` 服务模块
    - 实现 generate_api_key() 函数：生成 `yk_` 前缀 + 32位随机字符
    - 实现 hash_api_key() 函数：SHA256 哈希
    - 实现 create_api_key() 函数：创建并返回明文密钥（仅一次）
    - 实现 list_api_keys() 函数：获取列表（不含明文）
    - 实现 get_api_key() 函数：获取单个 API Key
    - 实现 update_api_key() 函数：更新 API Key
    - 实现 delete_api_key() 函数：删除 API Key
    - 实现 validate_api_key() 函数：验证密钥有效性
    - 实现 update_last_used() 函数：更新最后使用时间
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 3.1, 4.1, 4.3, 5.6_

  - [x] 2.2 编写 API Key 服务单元测试
    - 测试密钥生成格式
    - 测试哈希计算
    - **Property 1: API Key 格式一致性**
    - **Property 2: 密钥存储安全性**
    - **Validates: Requirements 1.2, 1.4**

- [x] 3. API Key 认证依赖实现
  - [x] 3.1 创建 `server/utils/apikey_auth.py` 认证模块
    - 实现 get_api_key_from_header() 函数：从 Authorization 头提取 API Key
    - 实现 validate_api_key_auth() 依赖：验证 API Key 有效性
    - 实现 require_scopes() 依赖工厂：检查权限范围
    - 处理各种错误情况：401/403 响应
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 6.1.3_

  - [ ]* 3.2 编写认证依赖单元测试
    - 测试有效密钥认证
    - 测试无效密钥拒绝
    - 测试权限范围验证
    - **Property 4: 有效密钥认证成功**
    - **Property 5: 无效/删除密钥返回 401**
    - **Property 7: 禁用密钥返回 403**
    - **Property 9: 权限范围验证**
    - **Validates: Requirements 5.1, 5.2, 5.3, 5.5, 6.1.3**

- [x] 4. Checkpoint - 确保服务层测试通过
  - 确保所有测试通过，如有问题请询问用户。

- [x] 5. API Key 管理路由实现
  - [x] 5.1 创建 `server/routers/apikey_router.py` 管理路由
    - POST /api/apikeys - 创建 API Key
    - GET /api/apikeys - 获取 API Key 列表
    - GET /api/apikeys/{key_id} - 获取单个 API Key
    - PUT /api/apikeys/{key_id} - 更新 API Key
    - DELETE /api/apikeys/{key_id} - 删除 API Key
    - PUT /api/apikeys/{key_id}/toggle - 启用/禁用 API Key
    - GET /api/apikeys/scopes - 获取可用权限范围列表
    - 所有接口需要管理员权限
    - _Requirements: 1.1, 2.1, 2.2, 2.3, 3.1, 4.1, 4.3, 6.1.1_

  - [x] 5.2 在 `server/routers/__init__.py` 中注册 apikey 路由
    - _Requirements: 1.1_

- [x] 6. 开放 API 路由实现
  - [x] 6.1 创建 `server/routers/open_api_router.py` 开放接口路由
    - GET /api/v1/open/knowledge/databases - 获取知识库列表（需要 knowledge:list 权限）
    - POST /api/v1/open/knowledge/databases/{db_id}/query - 查询知识库（需要 knowledge:read 权限）
    - 使用 require_scopes() 依赖进行权限验证
    - _Requirements: 6.1, 6.2.1, 6.2.2, 6.2.3, 6.2.4_

  - [x] 6.2 在 `server/routers/__init__.py` 中注册 open_api 路由
    - _Requirements: 6.1_

  - [x] 6.3 编写开放 API 集成测试
    - 测试知识库列表接口
    - 测试知识库查询接口
    - 测试权限验证
    - **Property 9: 权限范围验证**
    - **Validates: Requirements 6.2.1, 6.2.3, 6.1.3**

- [x] 7. Checkpoint - 确保后端接口测试通过
  - 确保所有测试通过，如有问题请询问用户。

- [x] 8. 前端 API 层实现
  - [x] 8.1 创建 `web/src/apis/apikey_api.js` API 模块
    - createApiKey(data) - 创建 API Key
    - getApiKeys() - 获取 API Key 列表
    - updateApiKey(keyId, data) - 更新 API Key
    - deleteApiKey(keyId) - 删除 API Key
    - toggleApiKey(keyId) - 启用/禁用 API Key
    - getAvailableScopes() - 获取可用权限范围
    - _Requirements: 8.1, 8.2, 8.5, 8.6_

- [x] 9. 前端管理组件实现
  - [x] 9.1 创建 `web/src/components/ApiKeyManagementComponent.vue` 管理组件
    - API Key 列表展示（卡片式布局）
    - 创建 API Key 模态框（名称、描述、权限范围、过期时间）
    - 创建成功后显示完整密钥并提供复制功能
    - 启用/禁用开关
    - 删除确认对话框
    - 使用 Ant Design Vue 组件
    - 使用 base.css 中的颜色变量
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

  - [x] 9.2 在 Dashboard 或设置页面中集成 API Key 管理组件
    - 添加 API Key 管理入口
    - _Requirements: 8.1_

- [x] 10. Checkpoint - 确保前端功能正常
  - 确保所有功能正常，如有问题请询问用户。

- [x] 11. 频率限制实现（可选）
  - [x]* 11.1 在 `server/utils/apikey_auth.py` 中添加频率限制逻辑
    - 使用内存缓存记录请求次数
    - 实现每分钟最大请求数限制
    - 返回 429 错误和 Retry-After 头
    - _Requirements: 7.1, 7.2, 7.3_

- [x] 12. 最终检查点
  - 确保所有测试通过，如有问题请询问用户。

## Notes

- 任务按照模块化原则组织，每个模块职责单一
- 标记 `*` 的任务为可选测试任务
- 每个任务都引用了对应的需求编号
- 属性测试验证核心正确性属性
- 频率限制作为可选功能，可根据需要实现
