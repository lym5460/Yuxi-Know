# Implementation Plan: Voice Agent Interaction

## Overview

本实现计划将语音智能体交互功能分解为可执行的编码任务。采用增量开发方式，每个任务都建立在前一个任务的基础上，确保代码始终可运行。

## Tasks

- [x] 1. 创建语音智能体基础结构
  - [x] 1.1 创建 `src/agents/voice_agent/` 目录结构
    - 创建 `__init__.py`, `graph.py`, `context.py`, `metadata.toml`
    - _Requirements: 1.1, 1.2, 1.3_
  - [x] 1.2 实现 VoiceContext 配置类
    - 继承 BaseContext，添加 ASR/TTS/VAD 配置字段
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_
  - [x] 1.3 实现 VoiceAgent 基础类
    - 继承 BaseAgent，实现 get_graph 方法
    - _Requirements: 1.1, 1.4, 1.5_
  - [ ]* 1.4 编写 VoiceAgent 单元测试
    - 测试继承关系和配置加载
    - **Property 1: Voice Agent Inheritance**
    - **Property 3: Configuration Loading**
    - **Validates: Requirements 1.1, 1.2, 1.3**

- [x] 2. 实现语音服务层
  - [x] 2.1 创建 `src/services/voice/` 目录结构
    - 创建 `__init__.py`, `asr_service.py`, `tts_service.py`, `vad_service.py`
    - _Requirements: 3.1, 4.1_
  - [x] 2.2 实现 ASR 服务接口和 OpenAI 实现
    - 定义 ASRService Protocol
    - 实现 OpenAIASRService（流式识别）
    - _Requirements: 3.1, 3.2, 3.3, 3.4_
  - [x] 2.3 实现 TTS 服务接口和 Edge-TTS 实现
    - 定义 TTSService Protocol
    - 实现 EdgeTTSService（流式合成）
    - _Requirements: 4.1, 4.2, 4.3_
  - [x] 2.4 实现 VAD 服务
    - 使用 Silero VAD 模型
    - 实现语音活动检测和语音结束检测
    - _Requirements: 3.6_
  - [ ]* 2.5 编写语音服务属性测试
    - **Property 4: Service Provider Factory**
    - **Property 5: Streaming ASR Output**
    - **Property 6: Streaming TTS Output**
    - **Property 7: VAD Speech Detection**
    - **Validates: Requirements 3.1, 3.2, 4.1, 4.2, 3.6**

- [x] 3. Checkpoint - 确保语音服务测试通过
  - 确保所有测试通过，如有问题请询问用户

- [x] 4. 实现 WebSocket 通信层
  - [x] 4.1 创建 `server/routers/voice_router.py`
    - 实现 WebSocket 端点 `/ws/voice/{agent_id}`
    - 实现消息协议解析和验证
    - _Requirements: 12.1, 12.4, 12.5_
  - [x] 4.2 实现 VoiceSessionManager
    - 管理 WebSocket 连接和会话状态
    - 实现会话超时处理
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.6_
  - [x] 4.3 实现音频流处理
    - 接收客户端音频块
    - 发送 TTS 音频块
    - 支持全双工通信
    - _Requirements: 2.1, 2.4, 2.5, 2.7_
  - [ ]* 4.4 编写 WebSocket 处理属性测试
    - **Property 19: WebSocket Message Validation**
    - **Property 20: Authentication Enforcement**
    - **Property 23: Full-Duplex Communication**
    - **Validates: Requirements 12.4, 12.5, 2.7**

- [x] 5. 实现打断处理
  - [x] 5.1 实现 InterruptHandler
    - 检测用户打断（VAD 检测到语音时 TTS 正在播放）
    - 停止 TTS 播放和取消待处理合成
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_
  - [ ]* 5.2 编写打断处理属性测试
    - **Property 8: Interruption Handling**
    - **Property 9: Interruption Sensitivity**
    - **Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5**

- [x] 6. 实现工具调用语音反馈
  - [x] 6.1 实现 ToolFeedbackMiddleware
    - 在工具调用时生成语音反馈
    - 支持可配置的详细程度
    - _Requirements: 10.1, 10.2, 10.3, 10.4_
  - [ ]* 6.2 编写工具反馈属性测试
    - **Property 16: Tool Feedback Generation**
    - **Property 17: Tool Result Summarization**
    - **Property 18: Tool Feedback Verbosity**
    - **Validates: Requirements 10.1, 10.2, 10.3, 10.4**

- [x] 7. Checkpoint - 确保后端功能测试通过
  - 确保所有测试通过，如有问题请询问用户

- [x] 8. 实现前端语音 API
  - [x] 8.1 创建 `web/src/apis/voice_api.js`
    - 实现 WebSocket 连接管理
    - 实现语音配置 API 调用
    - _Requirements: 12.1, 12.3_

- [x] 9. 实现前端音频处理
  - [x] 9.1 创建 `web/src/composables/useAudioCapture.js`
    - 使用 getUserMedia 采集音频
    - 配置回声消除和降噪
    - 实现音频块编码和发送
    - _Requirements: 2.2, 9.1, 9.2, 9.4_
  - [x] 9.2 创建 `web/src/composables/useAudioPlayer.js`
    - 使用 Web Audio API 播放音频
    - 实现流式音频缓冲
    - _Requirements: 2.8, 9.6_

- [x] 10. 实现前端语音组件
  - [x] 10.1 创建 `web/src/components/voice/VoiceChat.vue`
    - 语音聊天核心组件
    - 管理 WebSocket 连接和状态
    - _Requirements: 8.4, 8.5, 8.6_
  - [x] 10.2 创建 `web/src/components/voice/AudioVisualizer.vue`
    - 音频波形可视化
    - _Requirements: 8.3_
  - [x] 10.3 创建 `web/src/components/voice/VoiceControls.vue`
    - 语音控制按钮（开始/停止/静音）
    - 支持按住说话和语音激活模式
    - _Requirements: 8.6_

- [x] 11. 实现语音智能体视图
  - [x] 11.1 将语音 UI 集成到 AgentChatComponent.vue
    - 当选择语音智能体时显示语音交互界面（麦克风按钮）
    - 响应式布局适配多端
    - _Requirements: 8.1, 8.2, 8.7_
  - [x] 11.2 移除独立路由配置
    - 语音功能通过智能体选择触发，无需独立路由
    - _Requirements: 8.1_

- [x] 12. 实现错误处理和降级
  - [x] 12.1 实现前端错误处理
    - ASR/TTS 不可用时的降级处理
    - 网络错误提示
    - _Requirements: 11.1, 11.2, 11.3_
  - [x] 12.2 实现后端错误处理
    - 指数退避重试
    - 错误日志记录
    - _Requirements: 11.4, 11.5, 11.6_
  - [ ]* 12.3 编写错误处理属性测试
    - **Property 21: Exponential Backoff**
    - **Property 22: Error Logging Context**
    - **Validates: Requirements 11.4, 11.6**

- [x] 13. 集成和完善
  - [x] 13.1 注册 VoiceAgent 到 agent_manager
    - 在 `src/agents/__init__.py` 中注册
    - _Requirements: 1.1_
  - [x] 13.2 添加环境变量配置
    - 更新 `.env.template` 添加语音相关配置
    - _Requirements: 7.2, 7.3_

- [x] 14. Final Checkpoint - 确保所有测试通过
  - 确保所有测试通过，如有问题请询问用户

## Notes

- 任务标记 `*` 的为可选测试任务，可跳过以加快 MVP 开发
- 每个任务都引用了具体的需求条款以确保可追溯性
- 属性测试验证通用正确性属性
- 单元测试验证具体示例和边界情况
- Checkpoint 任务确保增量验证
