# Requirements Document

## Introduction

本文档定义了音视频知识库播放功能的需求。该功能允许用户创建专门用于音视频文件的知识库，通过集成 Memeries API 进行音视频内容分析和语义搜索，使语音智能体能够根据用户的语音指令搜索并播放音视频的特定片段。

## Glossary

- **Media_Knowledge_Base**: 专门用于处理音视频文件的知识库类型，使用 Memeries API 进行内容分析，类型标识为 `memeries`
- **Memeries_Service**: 集成 Memeries API 的服务组件，负责音视频上传、处理和语义搜索
- **Media_Search_Tool**: 提供给智能体的音视频搜索工具，返回媒体片段和时间戳信息
- **Media_Player**: 前端媒体播放器组件，支持播放音频和视频，并跳转到指定时间点
- **Voice_Agent**: 语音智能体，通过语音交互触发音视频搜索和播放
- **Media_Segment**: 媒体片段信息，包含 videoNo、媒体类型（audio/video）、startTime、endTime 和 score
- **videoNo**: Memeries API 返回的视频唯一标识符，格式为 `VI` 前缀加数字
- **unique_id**: Memeries API 中用于区分不同工作空间/用户的标识符

## Requirements

### Requirement 1: 音视频知识库类型

**User Story:** As a 用户, I want to 创建专门用于音视频文件的知识库, so that 我可以对音视频内容进行语义搜索和智能检索。

#### Acceptance Criteria

1. THE Media_Knowledge_Base SHALL 作为一种新的知识库类型在系统中注册，类型标识为 `memeries`
2. WHEN 用户创建知识库时 THEN THE 系统 SHALL 提供 `memeries` 类型选项供用户选择
3. THE Media_Knowledge_Base SHALL 接受以下格式文件：
   - 视频格式：h264、h265、vp9、hevc 编码的 mp4、avi、mov、mkv、webm 文件
   - 音频格式：mp3、wav、m4a、flac、aac、ogg
4. WHEN 用户上传非音视频文件到媒体知识库 THEN THE 系统 SHALL 拒绝上传并返回格式不支持的错误信息
5. THE Media_Knowledge_Base SHALL 使用知识库 db_id 作为 Memeries API 的 unique_id 参数
6. THE Media_Knowledge_Base SHALL 存储每个文件对应的 Memeries videoNo 用于后续查询和删除

### Requirement 2: Memeries API 集成 - 上传

**User Story:** As a 系统, I want to 集成 Memeries Upload API, so that 音视频内容可以被上传和索引。

#### Acceptance Criteria

1. THE Memeries_Service SHALL 调用 `POST /serve/api/v1/upload` 接口上传媒体文件
2. WHEN 上传文件时 THEN THE Memeries_Service SHALL 在请求中包含：
   - file: 媒体文件二进制数据
   - unique_id: 知识库 db_id
   - retain_original_video: true（保留原始文件）
3. WHEN 上传成功 THEN THE Memeries_Service SHALL 保存返回的 videoNo 到文件元数据
4. THE Memeries_Service SHALL 处理以下 videoStatus 状态：
   - UNPARSE: 未处理，等待处理
   - PARSE: 处理完成
   - FAIL: 处理失败
5. IF Memeries API 返回错误 THEN THE Memeries_Service SHALL 将文件状态标记为 error_indexing 并记录错误信息

### Requirement 3: Memeries API 集成 - 搜索

**User Story:** As a 系统, I want to 集成 Memeries Search API, so that 可以对音视频内容进行语义搜索。

#### Acceptance Criteria

1. THE Memeries_Service SHALL 调用 `POST /serve/api/v1/search` 接口执行语义搜索
2. WHEN 搜索时 THEN THE Memeries_Service SHALL 支持以下 search_type：
   - BY_VIDEO: 按视频内容搜索
   - BY_AUDIO: 按音频内容搜索
3. THE Memeries_Service SHALL 在搜索请求中包含：
   - search_param: 用户查询文本
   - search_type: 搜索类型
   - unique_id: 知识库 db_id
   - top_k: 返回结果数量（默认 5）
4. THE Memeries_Service SHALL 解析搜索响应，提取 videoNo、startTime、endTime、score 字段
5. WHEN 搜索无结果时 THEN THE Memeries_Service SHALL 返回空列表

### Requirement 4: Memeries API 集成 - 管理

**User Story:** As a 系统, I want to 集成 Memeries 管理 API, so that 可以查询和删除媒体文件。

#### Acceptance Criteria

1. THE Memeries_Service SHALL 调用 `POST /serve/api/v1/list_videos` 获取视频列表
2. THE Memeries_Service SHALL 调用 `GET /serve/api/v1/get_private_video_details` 获取视频详情，包括 duration、video_url、status
3. THE Memeries_Service SHALL 调用 `POST /serve/api/v1/delete_videos` 删除视频
4. WHEN 删除视频时 THEN THE Memeries_Service SHALL 发送 videoNo 数组，每次最多 100 个
5. THE Memeries_Service SHALL 使用视频详情中的 video_url 作为播放地址，如果为空则使用 MinIO 存储的原始文件

### Requirement 5: 媒体知识库检索器

**User Story:** As a 智能体, I want to 通过知识库检索器搜索媒体内容, so that 我可以根据用户查询搜索相关音视频片段。

#### Acceptance Criteria

1. THE Media_Knowledge_Base SHALL 提供检索器（retriever），遵循现有知识库检索器接口
2. WHEN 智能体绑定 memeries 类型知识库 THEN THE 系统 SHALL 自动为该智能体生成对应的媒体检索工具
3. THE 媒体检索工具 SHALL 接受以下参数：
   - query_text: 搜索关键词（必填）
   - operation: 操作类型，默认 "search"
4. THE 媒体检索工具 SHALL 返回匹配的媒体片段列表，每个片段包含：
   - media_id: Memeries videoNo
   - media_name: 文件名
   - media_type: video 或 audio
   - start_time: 片段开始时间（秒）
   - end_time: 片段结束时间（秒）
   - score: 相关性分数
   - media_url: 播放地址
5. THE 检索器 SHALL 同时执行 BY_VIDEO 和 BY_AUDIO 搜索并合并结果
6. THE 检索工具 SHALL 对所有类型的智能体可用（chatbot、voice_agent、deep_agent 等）

### Requirement 6: 媒体播放能力

**User Story:** As a 用户, I want to 在浏览器中播放音视频并跳转到指定时间点, so that 我可以直接收听/观看智能体找到的相关片段。

#### Acceptance Criteria

1. THE Media_Player SHALL 根据 media_type 渲染对应的播放器（video 元素或 audio 元素）
2. WHEN 接收到播放指令时 THEN THE Media_Player SHALL 设置 currentTime 为 start_time 并调用 play()
3. THE Media_Player SHALL 显示播放控制功能：播放/暂停、进度条、音量控制
4. THE Media_Player SHALL 为视频提供全屏按钮
5. THE Media_Player SHALL 在播放器上方显示片段描述信息
6. WHEN 媒体 URL 无效或加载失败 THEN THE Media_Player SHALL 显示错误提示

### Requirement 7: 聊天界面媒体播放

**User Story:** As a 用户, I want to 在聊天界面中查看搜索结果并播放媒体, so that 我可以通过文字对话找到并播放音视频内容。

#### Acceptance Criteria

1. WHEN 智能体返回媒体搜索结果 THEN THE 聊天界面 SHALL 以卡片形式展示搜索结果
2. THE 媒体结果卡片 SHALL 显示：媒体名称、媒体类型图标、时间范围（startTime - endTime）、相关性分数
3. WHEN 用户点击媒体结果卡片 THEN THE 系统 SHALL 打开媒体播放器并跳转到指定时间点播放
4. THE 媒体播放器 SHALL 以模态框或侧边栏形式展示，不离开聊天界面
5. THE 聊天界面 SHALL 支持同时显示多个搜索结果供用户选择

### Requirement 8: 语音智能体媒体交互

**User Story:** As a 用户, I want to 通过语音命令搜索和播放音视频, so that 我可以免手操作地查找和收听/观看内容。

#### Acceptance Criteria

1. WHEN 语音智能体绑定了 memeries 类型知识库 THEN THE Voice_Agent SHALL 自动获得媒体检索能力
2. THE Voice_Agent SHALL 通过 WebSocket 发送播放指令到前端
3. THE 播放指令 SHALL 使用以下 JSON 格式：
   ```json
   {
     "type": "media_command",
     "data": {
       "action": "play",
       "media_id": "VI123456",
       "media_type": "video",
       "media_url": "http://...",
       "start_time": 13,
       "end_time": 18,
       "description": "片段描述"
     }
   }
   ```
4. THE 播放指令 SHALL 支持以下 action 类型：play、pause、seek、stop
5. WHEN 前端接收到无效的播放指令 THEN THE 前端 SHALL 忽略该指令并在控制台记录警告

### Requirement 9: 媒体文件管理

**User Story:** As a 用户, I want to 管理媒体知识库中的文件, so that 我可以上传、查看和删除音视频文件。

#### Acceptance Criteria

1. THE 系统 SHALL 显示媒体文件的处理状态：
   - uploaded: 已上传到 MinIO
   - indexing: 正在 Memeries 处理中
   - indexed: Memeries 处理完成（PARSE）
   - error_indexing: 处理失败（FAIL）
2. THE 系统 SHALL 显示媒体文件信息：文件名、媒体类型图标、时长（duration）、大小（size）、上传时间
3. WHEN 用户删除媒体文件 THEN THE 系统 SHALL 同时：
   - 删除 MinIO 中的原始文件
   - 调用 Memeries delete_videos API 删除索引
4. WHEN 媒体处理失败 THEN THE 系统 SHALL 提供"重新处理"按钮

### Requirement 10: 配置管理

**User Story:** As a 系统管理员, I want to 配置 Memeries API 连接信息, so that 系统可以正确连接到 Memeries 服务。

#### Acceptance Criteria

1. THE 系统 SHALL 支持以下环境变量配置：
   - MEMERIES_API_ENDPOINT: API 地址，默认 `https://api.memories.ai`
   - MEMERIES_API_KEY: API 密钥（必填）
2. WHEN MEMERIES_API_KEY 未配置 THEN THE 系统 SHALL 在创建 memeries 类型知识库时返回配置错误
3. THE 系统 SHALL 在 Memeries_Service 初始化时验证 API Key 格式
4. IF API 配置无效 THEN THE 系统 SHALL 记录警告日志但不阻止系统启动
