# Project Structure

## Root Layout

```
yuxi-know/
├── .kiro/              # Kiro AI assistant configuration
├── docker/             # Docker configurations and volumes
├── docs/               # VitePress documentation site
├── openspec/           # OpenSpec change proposals and specs
├── saves/              # Runtime data (databases, logs, knowledge bases)
├── scripts/            # Utility scripts
├── server/             # FastAPI server entry point
├── src/                # Backend Python source code
├── test/               # Backend tests
└── web/                # Frontend Vue.js application
```

## Backend Structure (`src/`)

```
src/
├── agents/             # LangGraph agent implementations
│   ├── chatbot/        # Basic chatbot agent
│   ├── deep_agent/     # Deep analysis agent with file system
│   ├── mini_agent/     # Minimal agent
│   ├── reporter/       # Reporting agent
│   └── common/         # Shared agent utilities
│       ├── base.py     # Base agent classes
│       ├── context.py  # Context management
│       ├── middlewares/# Agent middlewares
│       ├── subagents/  # Sub-agent implementations
│       ├── toolkits/   # Tool collections
│       └── tools.py    # Common tools
├── config/             # Application configuration
│   └── static/         # Static config files (models, keywords)
├── knowledge/          # Knowledge base implementations
│   ├── adapters/       # KB adapters (LightRAG, upload)
│   ├── implementations/# KB backends (Milvus, LightRAG)
│   └── services/       # KB services (graph upload)
├── models/             # LLM model wrappers (chat, embed, rerank)
├── plugins/            # Document processors (MinerU, PaddleX, OCR)
├── services/           # Business services (doc converter, evaluation, MCP)
├── storage/            # Data persistence
│   ├── conversation/   # Chat history management
│   ├── db/             # Database models and manager
│   └── minio/          # Object storage client
└── utils/              # Utility functions
```

## Frontend Structure (`web/src/`)

```
web/src/
├── apis/               # API client modules (MUST define all API calls here)
├── assets/             # Static assets (CSS, icons, images)
│   └── css/base.css    # Theme CSS variables (MUST use for colors)
├── components/         # Vue components
│   ├── dashboard/      # Dashboard-specific components
│   ├── modals/         # Modal dialogs
│   └── ToolCallingResult/ # Tool result renderers
├── composables/        # Vue composables (reusable logic)
├── layouts/            # Layout components
├── router/             # Vue Router configuration
├── stores/             # Pinia state stores
├── utils/              # Frontend utilities
│   └── templates/      # Template utilities
├── views/              # Page-level components
├── App.vue             # Root component
└── main.js             # Application entry point
```

## Server Structure (`server/`)

```
server/
├── routers/            # FastAPI route handlers
├── services/           # Server-level services (tasker)
├── utils/              # Server utilities (auth, middleware, migration)
└── main.py             # FastAPI application entry point
```

## Data Directories

```
saves/
├── agents/             # Agent-specific data (history databases)
├── config/             # Runtime configuration (base.toml, custom_providers.toml)
├── database/           # SQLite database (server.db)
├── knowledge_base_data/# Knowledge base storage
│   └── lightrag_data/  # LightRAG graph data
├── knowledge_graph/    # Neo4j data
├── logs/               # Application logs
└── tasks/              # Task queue data
```

## Docker Volumes

```
docker/volumes/
├── milvus/             # Milvus vector database data
│   ├── etcd/           # etcd data
│   ├── minio/          # MinIO object storage
│   └── milvus/         # Milvus data and logs
├── neo4j/              # Neo4j graph database data
└── paddlex/            # PaddleX OCR data
```

## Key Conventions

### Backend
- Agent definitions in `src/agents/{agent_name}/`
- Each agent has: `__init__.py`, `graph.py`, `context.py` (optional), `tools.py` (optional)
- Knowledge base adapters in `src/knowledge/adapters/`
- API routers in `server/routers/`
- Tests in `test/` directory, scripts in `scripts/`

### Frontend
- **API calls MUST be defined in `web/src/apis/`** - never inline in components
- **Colors MUST use CSS variables from `web/src/assets/css/base.css`**
- Icons from `@ant-design/icons-vue` or `lucide-vue-next` (preferred)
- Styling with Less preprocessor
- Component naming: PascalCase for files, kebab-case in templates

### Documentation
- Main docs in `docs/latest/` (always update latest version)
- Developer docs in `docs/vibe/` (create only when necessary)
- Documentation config in `docs/.vitepress/config.mts`

### Configuration
- Environment variables in `.env` (copy from `.env.template`)
- Model providers in `saves/config/custom_providers.toml`
- Agent configs in `saves/agents/{agent_name}/config.yaml`
