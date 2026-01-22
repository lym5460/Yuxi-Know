# Technology Stack

## Architecture

Full-stack application managed entirely via Docker Compose with hot-reload for development.

## Backend

- **Framework**: FastAPI + Python 3.12+
- **Agent Framework**: LangGraph v1 (LangChain v1)
- **Package Manager**: uv (Python)
- **Database**: SQLite (via aiosqlite/asyncpg), Neo4j (graph), Milvus (vector)
- **Storage**: MinIO (object storage)
- **Key Libraries**:
  - LightRAG (knowledge graph RAG)
  - LangChain ecosystem (OpenAI, HuggingFace, DeepSeek, Tavily)
  - MinerU (document parsing)
  - RapidOCR (OCR processing)

## Frontend

- **Framework**: Vue 3 + Vite
- **Package Manager**: pnpm
- **UI Library**: Ant Design Vue
- **State Management**: Pinia with persistence
- **Visualization**: 
  - ECharts (charts)
  - Sigma.js + Graphology (2D graphs)
  - 3D Force Graph (3D visualization)
  - Markmap (mind maps)
- **Styling**: Less with CSS variables for theming

## Infrastructure

- **Containerization**: Docker Compose
- **Services**: api-dev, web-dev, graph (Neo4j), milvus, etcd, minio, mineru-vllm-server, mineru-api, paddlex
- **Hot Reload**: Enabled for both api-dev and web-dev services

## Common Commands

### Development

```bash
# Start all services (requires .env file)
make start
# or
docker compose up -d

# Stop services
make stop
# or
docker compose down

# View logs
make logs
# or
docker logs api-dev --tail 100
docker logs web-dev --tail 100

# Check running containers
docker ps
```

### Backend

```bash
# Lint and format Python code
make lint          # Check code style
make format        # Auto-fix formatting issues

# Run tests
make router-tests  # Run API router tests

# Execute scripts in container
docker compose exec api uv run python test/your_script.py
```

### Frontend

```bash
# NEVER run these commands directly - services run in containers
# pnpm run dev
# pnpm run server

# Lint frontend code (if needed, run in container)
docker compose exec web pnpm run lint
```

### Documentation

```bash
# Run documentation site locally
npm run docs:dev
npm run docs:host  # With host access
npm run docs:build
```

## Development Workflow

1. Ensure `.env` file exists (copy from `.env.template`)
2. Start services: `make start` or `docker compose up -d`
3. Check service status: `docker ps`
4. View logs if issues: `docker logs api-dev --tail 100`
5. Edit code locally - changes auto-reload in containers
6. No need to restart containers for code changes

## Python Code Style

- Follow PEP 8 and Pythonic conventions
- Use modern Python 3.12+ syntax
- Configured with Ruff for linting and formatting
- Line length: 120 characters
- Async/await patterns for I/O operations
