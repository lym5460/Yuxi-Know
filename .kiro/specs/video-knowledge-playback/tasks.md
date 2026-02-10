# Implementation Tasks: Video Knowledge Playback

## Task 1: Memeries Service 实现
实现 Memeries API 封装服务，提供上传、搜索、管理等功能。

- [x] 1.1 创建 `src/services/memeries_service.py` 文件
  - 实现 `MemeriesService` 类
  - 从环境变量读取 `MEMERIES_API_ENDPOINT` 和 `MEMERIES_API_KEY`
  - 实现 `upload()` 方法：POST /serve/api/v1/upload
  - 实现 `search()` 方法：POST /serve/api/v1/search
  - 实现 `list_videos()` 方法：POST /serve/api/v1/list_videos
  - 实现 `get_video_details()` 方法：GET /serve/api/v1/get_private_video_details
  - 实现 `delete_videos()` 方法：POST /serve/api/v1/delete_videos
  - **Validates: Requirements 2.1, 2.2, 3.1, 3.3, 4.1, 4.2, 4.3, 4.4**

- [x] 1.2 Property Test: 文件格式验证 (Property 1)
  - 测试 `_validate_file_format` 对所有支持格式返回 True
  - 测试 `_get_media_type` 正确返回 video/audio/unknown
  - **Validates: Requirements 1.3, 1.4**

## Task 2: Memeries Knowledge Base 实现
实现基于 Memeries API 的媒体知识库。

- [x] 2.1 创建 `src/knowledge/implementations/memeries.py` 文件
  - 继承 `KnowledgeBase` 基类
  - 定义 `SUPPORTED_VIDEO_FORMATS` 和 `SUPPORTED_AUDIO_FORMATS`
  - 实现 `kb_type` 属性返回 "memeries"
  - 实现 `_validate_file_format()` 和 `_get_media_type()` 方法
  - **Validates: Requirements 1.1, 1.3, 1.4**

- [x] 2.2 实现 `index_file()` 方法
  - 调用 Memeries upload API
  - 使用 db_id 作为 unique_id
  - 保存 videoNo 到文件元数据
  - 处理 videoStatus 状态映射 (UNPARSE→indexing, PARSE→indexed, FAIL→error_indexing)
  - **Validates: Requirements 1.5, 1.6, 2.3, 2.4, 2.5**

- [x] 2.3 实现 `aquery()` 方法
  - 同时执行 BY_VIDEO 和 BY_AUDIO 搜索
  - 合并结果并按 score 降序排列
  - 返回标准化的媒体片段格式
  - **Validates: Requirements 3.2, 3.4, 3.5, 5.4, 5.5**

- [x] 2.4 实现 `delete_file()` 方法
  - 删除 MinIO 中的文件
  - 调用 Memeries delete_videos API
  - **Validates: Requirements 9.3**

- [x] 2.5 实现其他必要方法
  - `_create_kb_instance()` 和 `_initialize_kb_instance()`
  - `update_content()` 方法
  - `get_file_basic_info()`, `get_file_content()`, `get_file_info()`
  - `get_query_params_config()` 返回 memeries 类型配置

- [x] 2.6 在工厂中注册 memeries 类型
  - 更新 `src/knowledge/implementations/__init__.py`
  - 在 `src/knowledge/manager.py` 中注册 MemeriesKB

## Task 3: Property Tests - 核心属性验证

- [x] 3.1 Property Test: API 请求参数完整性 (Property 2)
  - 验证上传请求包含 file、unique_id、retain_original_video
  - 验证搜索请求包含 search_param、search_type、unique_id、top_k
  - **Validates: Requirements 2.2, 3.3**

- [x] 3.2 Property Test: 状态映射正确性 (Property 3)
  - 验证 UNPARSE/PARSE/FAIL 状态正确映射
  - **Validates: Requirements 2.4, 2.5**

- [x] 3.3 Property Test: 搜索结果格式完整性 (Property 4)
  - 验证结果包含所有必需字段
  - 验证 start_time 和 end_time 是数字类型
  - **Validates: Requirements 3.4, 5.4**

- [x] 3.4 Property Test: 搜索类型合并 (Property 5)
  - 验证同时执行 BY_VIDEO 和 BY_AUDIO 搜索
  - 验证结果按 score 降序排列
  - **Validates: Requirements 3.2, 5.5**

## Task 4: 智能体工具集成
确保所有智能体类型都能使用媒体检索工具。

- [x] 4.1 更新 `src/agents/common/tools.py`
  - 在 `get_kb_based_tools()` 中支持 memeries 类型知识库
  - 为 memeries 类型创建专用的检索器包装函数
  - **Validates: Requirements 5.1, 5.2, 5.3, 5.6**

- [x] 4.2 Property Test: 工具自动绑定 (Property 6)
  - 验证绑定 memeries 知识库的智能体自动获得媒体检索工具
  - **Validates: Requirements 5.2, 8.1**

## Task 5: 前端媒体播放器组件

- [x] 5.1 创建 `web/src/components/MediaPlayer.vue`
  - 根据 media_type 渲染 video 或 audio 元素
  - 支持 seekAndPlay 功能
  - 显示播放控制和片段描述
  - **Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5**

- [x] 5.2 Property Test: 播放器类型选择 (Property 7)
  - 验证 video 类型渲染 video 元素
  - 验证 audio 类型渲染 audio 元素
  - **Validates: Requirements 6.1**

## Task 6: 聊天界面媒体结果展示

- [x] 6.1 创建 `web/src/components/ToolCallingResult/MediaResultCard.vue`
  - 显示媒体名称、类型图标、时间范围、相关性分数
  - 点击触发播放
  - **Validates: Requirements 7.1, 7.2, 7.3**

- [x] 6.2 更新聊天界面集成
  - 在工具调用结果中识别媒体搜索结果
  - 渲染 MediaResultCard 组件
  - 集成 MediaPlayer 模态框
  - **Validates: Requirements 7.4, 7.5**

## Task 7: 语音智能体媒体交互

- [x] 7.1 定义播放指令协议
  - 创建 `MediaPlayCommand` 数据模型
  - 定义 WebSocket 消息格式
  - **Validates: Requirements 8.3, 8.4**

- [x] 7.2 更新语音智能体 WebSocket 处理
  - 在 `server/routers/voice_router.py` 中支持发送 media_command 消息
  - **Validates: Requirements 8.2**

- [x] 7.3 前端 WebSocket 媒体指令处理
  - 在语音智能体视图中监听 media_command 消息
  - 触发 MediaPlayer 播放
  - **Validates: Requirements 8.5**

- [x] 7.4 Property Test: 播放指令协议验证 (Property 8)
  - 验证指令包含必需字段
  - 验证 action 类型有效性
  - 验证无效指令被忽略
  - **Validates: Requirements 8.3, 8.4, 8.5**

## Task 8: 知识库管理界面

- [x] 8.1 更新知识库创建界面
  - 添加 memeries 类型选项
  - **Validates: Requirements 1.2**

- [x] 8.2 更新文件列表显示
  - 显示媒体文件状态 (uploaded, indexing, indexed, error_indexing)
  - 显示媒体类型图标和时长
  - **Validates: Requirements 9.1, 9.2**

- [x] 8.3 实现重新处理功能
  - 为 error_indexing 状态的文件提供重新处理按钮
  - **Validates: Requirements 9.4**

## Task 9: 配置管理

- [x] 9.1 更新环境变量模板
  - 在 `.env.template` 中添加 MEMERIES_API_ENDPOINT 和 MEMERIES_API_KEY
  - **Validates: Requirements 10.1**

- [x] 9.2 实现配置验证
  - 在创建 memeries 知识库时检查 API Key 配置
  - **Validates: Requirements 10.2, 10.3, 10.4**

## Task 10: Property Tests - 删除和 URL 回退

- [x] 10.1 Property Test: 删除完整性 (Property 9)
  - 验证删除同时清理 MinIO 和 Memeries
  - **Validates: Requirements 9.3**

- [x] 10.2 Property Test: URL 回退逻辑 (Property 10)
  - 验证 video_url 为空时使用 MinIO URL
  - **Validates: Requirements 4.5**

## Task 11: 集成测试

- [ ]* 11.1 上传流程集成测试
  - Mock Memeries API 测试完整上传流程

- [ ]* 11.2 搜索流程集成测试
  - Mock Memeries API 测试搜索和结果合并

- [ ]* 11.3 端到端测试
  - 测试从上传到搜索到播放的完整流程
