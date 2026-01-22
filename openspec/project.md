# Project Context

## Purpose

**语析（Yuxi-Know）** 是一个功能强大的智能体开发平台，融合了 RAG 知识库与知识图谱技术。

### 核心目标
- 提供全套的智能体开发套件（基于 LangGraph v1 架构）
- 融合 RAG 检索增强生成与知识图谱技术
- 支持多模态输入（文本、图片、文档等）
- 提供知识库管理、评估与可视化功能
- 基于 MIT 开源协议，技术栈友好，适合二次开发

### 主要功能模块
- **智能体系统**: 支持工具调用、中间件、子智能体等开发套件
- **知识库管理**: 支持向量检索（Milvus）和图谱检索（LightRAG）
- **文档解析**: 支持 PDF、Word、Markdown、压缩包等多种格式，集成 MinerU、PaddleX OCR
- **知识图谱**: 基于 Neo4j，支持可视化与分析
- **对话管理**: 支持多轮对话、流式输出、消息重新生成

## Tech Stack

### 后端技术栈
- **语言**: Python 3.11+
- **框架**: FastAPI (异步 Web 框架)
- **包管理**: uv (快速 Python 包管理器)
- **智能体框架**: LangGraph v1, LangChain
- **数据库**: 
  - SQLite (with aiosqlite) - 主数据库
  - Neo4j 5.26 - 知识图谱
  - Milvus v2.5.6 - 向量数据库
- **对象存储**: MinIO
- **文档处理**: MinerU, Docling, Unstructured, LlamaIndex
- **AI 能力**: 
  - 支持 OpenAI、DeepSeek、通义千问等多种大模型
  - LightRAG (图谱增强检索)
  - RAG 检索增强生成
- **代码质量**: Ruff (linter + formatter), pytest

### 前端技术栈
- **框架**: Vue 3 (Composition API)
- **构建工具**: Vite 7
- **包管理**: pnpm 10
- **UI 库**: Ant Design Vue 4
- **图标**: @ant-design/icons-vue, lucide-vue-next (推荐)
- **样式**: Less (CSS 预处理器)
- **状态管理**: Pinia (with persistence)
- **路由**: Vue Router 4
- **图表可视化**: 
  - ECharts (含 echarts-gl 3D 图表)
  - Sigma.js + Graphology (图谱可视化)
  - 3D Force Graph
  - D3.js
- **编辑器**: md-editor-v3, markmap (思维导图)
- **工具库**: @vueuse/core, dayjs, marked

### 基础设施
- **容器化**: Docker + Docker Compose (完全容器化部署)
- **反向代理**: Nginx (生产环境)
- **开发模式**: 热重载 (api-dev 和 web-dev 服务)
- **外部服务**: 
  - etcd (Milvus 元数据存储)
  - MinIO (对象存储)

### 可选服务 (profile: all)
- **MinerU**: 高质量 PDF 解析（需要 GPU）
- **PaddleX**: OCR 服务（需要 GPU）

## Project Conventions

### Code Style

#### Python (后端)
- **风格指南**: 遵循 Pythonic 风格，使用 Python 3.12+ 现代语法
- **格式化工具**: Ruff (格式化 + lint)
- **代码规范**:
  - 最大行宽: 120 字符
  - 选择的规则: F (Pyflakes), E/W (pycodestyle), UP (pyupgrade)
  - 使用类型提示 (Type Hints)
  - 优先使用异步函数 (async/await)
- **命令**:
  - `make lint` - 检查代码规范
  - `make format` - 自动格式化代码

#### JavaScript/Vue (前端)
- **风格**: Vue 3 Composition API, 使用 `<script setup>` 语法
- **格式化**: Prettier + ESLint
- **样式约定**:
  - 使用 Less 预处理器
  - **必须**使用 `web/src/assets/css/base.css` 中定义的颜色变量
  - 避免悬停位移效果
  - 避免过度使用阴影和渐变色
  - 保持 UI 简洁一致
- **API 规范**: 所有 API 接口定义在 `web/src/apis` 目录下
- **Icon 使用**: 优先使用 `lucide-vue-next`（注意尺寸），其次 `@ant-design/icons-vue`

### Architecture Patterns

#### 整体架构
- **前后端分离**: Vue.js 前端 + FastAPI 后端
- **微服务思想**: 通过 Docker Compose 编排多个服务
- **异步优先**: 后端全面使用异步数据库操作和 API 调用
- **热重载开发**: 本地代码变更自动同步到容器

#### 后端架构模式
- **目录结构**:
  - `server/` - FastAPI 应用入口和路由
  - `src/` - 核心业务逻辑（智能体、知识库、工具等）
  - `src/plugins/` - 插件化功能模块
  - `saves/` - 数据持久化目录
  - `test/` - 测试和调试脚本
- **关键组件**:
  - `DBManager` - 异步数据库管理
  - `ConversationManager` - 对话状态管理
  - 智能体系统基于 LangGraph 的 `create_agent` 模式
  - 中间件机制支持扩展（文件上传、多模态等）

#### 前端架构模式
- **目录结构**:
  - `web/src/components/` - 可复用组件
  - `web/src/views/` - 页面视图
  - `web/src/apis/` - API 接口定义
  - `web/src/stores/` - Pinia 状态管理
  - `web/src/router/` - 路由配置
  - `web/src/assets/` - 静态资源（CSS、图片）

#### 设计原则
- **避免过度工程**: 仅实现必要功能，不添加未要求的特性
- **简单优先**: 优先选择简单方案，避免不必要的抽象
- **复用现有代码**: 遵循 DRY 原则，使用已有抽象
- **边界验证**: 仅在系统边界（用户输入、外部 API）进行验证
- **信任内部代码**: 不为内部调用添加冗余的错误处理

### Testing Strategy

#### 测试工具
- **框架**: pytest (with pytest-asyncio)
- **覆盖率**: pytest-cov
- **HTTP 测试**: pytest-httpx
- **配置**: `pyproject.toml` 中的 `[tool.pytest.ini_options]`

#### 测试分类
- `@pytest.mark.auth` - 需要认证的测试
- `@pytest.mark.slow` - 慢速测试
- `@pytest.mark.integration` - 集成测试

#### 运行测试
```bash
# 在容器内运行 API 测试
make router-tests

# 或直接调用
docker compose exec api uv run --group test pytest test/api
```

#### 测试策略
- 优先编写单元测试和集成测试
- 使用异步测试 (`pytest-asyncio`)
- 测试文件放在 `test/` 目录

### Git Workflow

#### 分支策略
- **main** - 稳定生产分支
- **develop** - 开发分支（如果使用）
- **feature/*** - 功能分支
- **fix/*** - 修复分支

#### 提交规范
- 遵循 Conventional Commits 风格（推荐）
- 使用清晰的提交信息，说明变更内容

#### 发布流程
- 使用语义化版本号（Semantic Versioning）
- 当前版本: v0.4.3

## Domain Context

### AI 智能体领域
- **智能体（Agent）**: 基于大语言模型的自主系统，能够使用工具、访问知识库、执行多步推理
- **LangGraph**: LangChain 团队开发的智能体框架，支持状态图、检查点、流式输出
- **中间件（Middleware）**: 在智能体调用前后执行的钩子函数，用于扩展功能
- **子智能体（Sub-Agent）**: 智能体可以调用其他智能体作为工具

### RAG 技术
- **检索增强生成**: 结合外部知识检索和生成模型，提高回答准确性
- **向量检索**: 使用 Milvus 向量数据库，通过语义相似度检索文档
- **重排序（Rerank）**: 对检索结果进行二次排序，提高相关性
- **Embeddings**: 文本向量化模型，支持多种 embedding 提供商

### 知识图谱
- **Neo4j**: 图数据库，存储实体和关系
- **LightRAG**: 图谱增强的 RAG 技术，结合向量检索和图谱推理
- **实体抽取**: 从文本中抽取实体和关系构建知识图谱
- **图谱可视化**: 使用 Sigma.js、ECharts GL 等进行交互式可视化

### 文档处理
- **MinerU**: 高质量 PDF 解析工具，支持表格、图片提取
- **Docling**: 现代文档解析库
- **OCR**: 光学字符识别，将图片转为文本（PaddleX）
- **分块策略**: 将长文档切分为适合检索的小块（Chunking）

## Important Constraints

### 技术约束
1. **Docker 环境强制要求**
   - 所有服务必须通过 Docker Compose 运行
   - 不允许直接在宿主机运行 npm/pnpm 开发服务器
   - 不允许直接在宿主机运行 Python 开发服务器

2. **热重载机制**
   - `api-dev` 和 `web-dev` 服务配置了热重载
   - 本地代码修改会自动同步到容器
   - **无需重启容器**，服务会自动更新

3. **Python 版本**
   - 最低要求: Python 3.11+
   - 目标版本: Python 3.12+
   - 避免使用旧版本语法

4. **依赖管理**
   - 后端使用 `uv` 而非 pip
   - 前端使用 `pnpm` 而非 npm/yarn
   - 不允许修改 git config

### 开发约束
1. **工作流检查**
   - 开始任务前检查服务是否已在后台运行 (`docker ps`)
   - 查看日志了解服务状态 (`docker logs api-dev --tail 100`)
   - 参考 `docker-compose.yml` 了解服务配置

2. **代码修改原则**
   - 仅做必要的修改，避免"改进"未要求的代码
   - Bug 修复不需要清理周围代码
   - 简单功能不需要额外的配置能力
   - 不为内部代码添加不必要的错误处理

3. **文档约束**
   - 文档保存在 `docs/vibe/` 文件夹（仅开发者可见）
   - **非必要不创建**说明文档
   - 代码更新后检查文档是否需要同步更新
   - 文档目录定义在 `docs/.vitepress/config.mts`
   - 更新最新版文档 (`docs/latest`)

4. **认证**
   - 使用 `YUXI_SUPER_ADMIN_NAME` / `YUXI_SUPER_ADMIN_PASSWORD` 调试接口
   - 基于 JWT 的认证机制

### 部署约束
- 生产环境使用 `uv export` 固定依赖版本
- 支持代理配置 (HTTP_PROXY, HTTPS_PROXY)
- 需要配置 `.env` 文件（从 `.env.template` 复制）

## External Dependencies

### 核心外部服务

#### 1. Neo4j (图数据库)
- **版本**: 5.26
- **端口**: 7474 (HTTP), 7687 (Bolt)
- **用途**: 知识图谱存储
- **连接**: `NEO4J_URI=bolt://graph:7687`
- **认证**: `NEO4J_USERNAME` / `NEO4J_PASSWORD`

#### 2. Milvus (向量数据库)
- **版本**: v2.5.6
- **端口**: 19530 (gRPC), 9091 (HTTP)
- **用途**: 向量检索
- **连接**: `MILVUS_URI=http://milvus:19530`
- **依赖**: etcd (元数据), MinIO (对象存储)

#### 3. MinIO (对象存储)
- **版本**: RELEASE.2023-03-20T20-16-18Z
- **端口**: 9000 (API), 9001 (Console)
- **用途**: 文件存储（文档、图片等）
- **连接**: `MINIO_URI=http://milvus-minio:9000`
- **认证**: `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY`

#### 4. etcd (键值存储)
- **版本**: v3.5.5
- **端口**: 2379
- **用途**: Milvus 元数据存储

### 可选外部服务 (Profile: all)

#### 5. MinerU (PDF 解析)
- **端口**: 30000 (vLLM 服务器), 30001 (API)
- **用途**: 高质量 PDF 文档解析
- **需求**: NVIDIA GPU
- **连接**: `MINERU_OCR_URI=http://mineru:30000`

#### 6. PaddleX (OCR)
- **端口**: 8080
- **用途**: 光学字符识别
- **需求**: NVIDIA GPU
- **连接**: `PADDLEX_URI=http://paddlex:8080`

### 大模型 API 服务

#### 支持的提供商
- **OpenAI**: GPT-3.5, GPT-4, GPT-4o 等
- **DeepSeek**: DeepSeek-V3, DeepSeek-Chat
- **通义千问 (DashScope)**: Qwen 系列
- **自定义兼容 OpenAI 的服务**: 支持自定义 base_url

#### 关键配置
- Embedding 模型: 用于文本向量化
- Chat 模型: 用于对话生成
- Rerank 模型: 用于检索结果重排序（可选）

### 工具和 API 服务
- **Tavily**: 网络搜索 API（可选）
- **LangSmith**: LangChain 的可观测性平台（可选）

### 开发工具
- **sqlite-web**: SQLite 数据库 Web 管理界面
  - 端口: 9092
  - 数据库路径: `saves/database/server.db`
