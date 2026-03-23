#!/bin/bash
# =============================================================================
# Yuxi-Know 生产部署包构建脚本
# 用法:
#   ./scripts/build_deploy_package.sh                        # 只打包基础服务
#   ./scripts/build_deploy_package.sh --ocr                  # + MinerU OCR（需要 GPU）
#   ./scripts/build_deploy_package.sh --paddlex              # + PaddleX OCR（需要 GPU）
#   ./scripts/build_deploy_package.sh --asr                  # + Whisper ASR（需要 GPU）
#   ./scripts/build_deploy_package.sh --ocr --paddlex --asr  # 组合
#   ./scripts/build_deploy_package.sh --all                  # 全部可选服务
#   ./scripts/build_deploy_package.sh --slim                 # 精简包（仅自定义镜像，配合 install.sh --online）
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}/.."

# ============================================================
# 解析参数
# ============================================================
BUILD_OCR=false
BUILD_PADDLEX=false
BUILD_ASR=false
SLIM_MODE=false  # --slim: 只打包自定义镜像，跳过第三方镜像（配合 install.sh --online 使用）
TARGET_PLATFORM="linux/amd64"  # 目标平台，默认 linux/amd64

for arg in "$@"; do
    case "${arg}" in
        --ocr)          BUILD_OCR=true ;;
        --paddlex)      BUILD_PADDLEX=true ;;
        --asr)          BUILD_ASR=true ;;
        --all)          BUILD_OCR=true; BUILD_PADDLEX=true; BUILD_ASR=true ;;
        --slim)         SLIM_MODE=true ;;
        --platform=*)   TARGET_PLATFORM="${arg#--platform=}" ;;
    esac
done

VERSION=$(grep '^version' pyproject.toml | head -1 | sed 's/version = "\(.*\)"/\1/')
PACKAGE_DIR="deploy-package"
BASE_TAR="yuxi-know-v${VERSION}-base.tar"
OCR_TAR="yuxi-know-v${VERSION}-ocr.tar"
PADDLEX_TAR="yuxi-know-v${VERSION}-paddlex.tar"
ASR_TAR="yuxi-know-v${VERSION}-asr.tar"

echo "======================================================"
echo "  Yuxi-Know 部署包构建脚本"
echo "  版本        : v${VERSION}"
echo "  目标平台    : ${TARGET_PLATFORM}"
echo "  精简打包    : ${SLIM_MODE}"
echo "  MinerU OCR  : ${BUILD_OCR}"
echo "  PaddleX OCR : ${BUILD_PADDLEX}"
echo "  Whisper ASR : ${BUILD_ASR}"
echo "======================================================"
echo ""

# 检查 buildx 是否可用（跨平台构建必需）
if ! docker buildx version &> /dev/null; then
    echo "[错误] 未检测到 docker buildx，请升级 Docker Desktop 到最新版"
    exit 1
fi

# ============================================================
# 第一步：构建自定义镜像 + 拉取第三方镜像（指定目标平台）
# ============================================================
echo "[1/5] 构建应用镜像 (api, web) —— 目标平台: ${TARGET_PLATFORM}..."
docker buildx build --platform "${TARGET_PLATFORM}" --load \
    -t yuxi-api:0.5.prod -f docker/api.Dockerfile .
docker buildx build --platform "${TARGET_PLATFORM}" --load \
    -t yuxi-web:0.5.prod -f docker/web.Dockerfile --target production .

if [ "${BUILD_OCR}" = true ]; then
    echo "[1/5] 构建 MinerU OCR 镜像..."
    docker buildx build --platform "${TARGET_PLATFORM}" --load \
        -t mineru-vllm:latest -f docker/mineru.Dockerfile .
fi

if [ "${BUILD_PADDLEX}" = true ]; then
    echo "[1/5] 构建 PaddleX OCR 镜像..."
    docker buildx build --platform "${TARGET_PLATFORM}" --load \
        -t paddlex:latest -f docker/paddlex.Dockerfile .
fi

# 拉取第三方镜像（显式指定平台，确保 M1 上不会拉成 arm64）
if [ "${SLIM_MODE}" = true ]; then
    echo "[1/5] 跳过第三方镜像拉取（精简模式，部署时使用 --online 在线拉取）"
else
    echo "[1/5] 拉取第三方镜像 (${TARGET_PLATFORM})..."
    THIRD_PARTY_IMAGES=(
        "postgres:16"
        "redis:7-alpine"
        "neo4j:5.26"
        "quay.io/coreos/etcd:v3.5.5"
        "minio/minio:RELEASE.2023-03-20T20-16-18Z"
        "milvusdb/milvus:v2.5.6"
    )
    for img in "${THIRD_PARTY_IMAGES[@]}"; do
        echo "  拉取 ${img}..."
        docker pull --platform "${TARGET_PLATFORM}" "${img}"
    done

    if [ "${BUILD_ASR}" = true ]; then
        echo "  拉取 fedirz/faster-whisper-server:latest-cuda..."
        docker pull --platform "${TARGET_PLATFORM}" "fedirz/faster-whisper-server:latest-cuda"
    fi
fi

# ============================================================
# 第二步：导出镜像为 tar 包
# ============================================================
echo ""
if [ "${SLIM_MODE}" = true ]; then
    echo "[2/5] 导出自定义镜像 → ${BASE_TAR}（精简模式，仅自定义镜像）..."
    CUSTOM_IMAGES=(
        "yuxi-api:0.5.prod"
        "yuxi-web:0.5.prod"
    )
    docker save "${CUSTOM_IMAGES[@]}" -o "${BASE_TAR}"
else
    echo "[2/5] 导出基础镜像 → ${BASE_TAR}（可能需要几分钟）..."
    BASE_IMAGES=(
        "yuxi-api:0.5.prod"
        "yuxi-web:0.5.prod"
        "postgres:16"
        "redis:7-alpine"
        "neo4j:5.26"
        "quay.io/coreos/etcd:v3.5.5"
        "minio/minio:RELEASE.2023-03-20T20-16-18Z"
        "milvusdb/milvus:v2.5.6"
    )
    docker save "${BASE_IMAGES[@]}" -o "${BASE_TAR}"
fi
echo "  基础镜像包大小: $(du -h ${BASE_TAR} | cut -f1)"

if [ "${BUILD_OCR}" = true ]; then
    echo "[2/5] 导出 MinerU OCR 镜像 → ${OCR_TAR}..."
    docker save "mineru-vllm:latest" -o "${OCR_TAR}"
    echo "  MinerU 镜像包大小: $(du -h ${OCR_TAR} | cut -f1)"
fi

if [ "${BUILD_PADDLEX}" = true ]; then
    echo "[2/5] 导出 PaddleX OCR 镜像 → ${PADDLEX_TAR}..."
    docker save "paddlex:latest" -o "${PADDLEX_TAR}"
    echo "  PaddleX 镜像包大小: $(du -h ${PADDLEX_TAR} | cut -f1)"
fi

if [ "${BUILD_ASR}" = true ]; then
    if [ "${SLIM_MODE}" = true ]; then
        echo "[2/5] 跳过 Whisper ASR 镜像导出（精简模式，部署时在线拉取）"
    else
        echo "[2/5] 导出 Whisper ASR 镜像 → ${ASR_TAR}..."
        docker save "fedirz/faster-whisper-server:latest-cuda" -o "${ASR_TAR}"
        echo "  Whisper 镜像包大小: $(du -h ${ASR_TAR} | cut -f1)"
    fi
fi

# ============================================================
# 第三步：准备部署包目录
# ============================================================
echo ""
echo "[3/5] 准备部署包目录..."

rm -rf "${PACKAGE_DIR}"
mkdir -p "${PACKAGE_DIR}/docker/nginx"
mkdir -p "${PACKAGE_DIR}/docker/volumes/neo4j/data"
mkdir -p "${PACKAGE_DIR}/docker/volumes/neo4j/logs"
mkdir -p "${PACKAGE_DIR}/docker/volumes/milvus/etcd"
mkdir -p "${PACKAGE_DIR}/docker/volumes/milvus/minio"
mkdir -p "${PACKAGE_DIR}/docker/volumes/milvus/minio_config"
mkdir -p "${PACKAGE_DIR}/docker/volumes/milvus/milvus"
mkdir -p "${PACKAGE_DIR}/docker/volumes/milvus/logs"
mkdir -p "${PACKAGE_DIR}/docker/volumes/postgresql"
mkdir -p "${PACKAGE_DIR}/docker/volumes/redis"
mkdir -p "${PACKAGE_DIR}/saves"
mkdir -p "${PACKAGE_DIR}/models"

cp docker-compose.prod.yml   "${PACKAGE_DIR}/"
cp docker/nginx/nginx.conf   "${PACKAGE_DIR}/docker/nginx/"
cp docker/nginx/default.conf "${PACKAGE_DIR}/docker/nginx/"
cp .env.template             "${PACKAGE_DIR}/.env.prod"

mv "${BASE_TAR}" "${PACKAGE_DIR}/"
[ "${BUILD_OCR}" = true ]                                         && mv "${OCR_TAR}"     "${PACKAGE_DIR}/"
[ "${BUILD_PADDLEX}" = true ]                                     && mv "${PADDLEX_TAR}" "${PACKAGE_DIR}/"
[ "${BUILD_ASR}" = true ] && [ "${SLIM_MODE}" != true ] && mv "${ASR_TAR}"     "${PACKAGE_DIR}/"

# ============================================================
# 第四步：生成 install.sh（嵌入构建时的可选服务信息）
# ============================================================
echo ""
echo "[4/5] 生成 install.sh..."

# 将构建时选择的可选 profile 写入安装脚本，供客户参考
OPTIONAL_PROFILES=""
[ "${BUILD_OCR}" = true ]     && OPTIONAL_PROFILES="${OPTIONAL_PROFILES} --ocr"
[ "${BUILD_PADDLEX}" = true ] && OPTIONAL_PROFILES="${OPTIONAL_PROFILES} --paddlex"
[ "${BUILD_ASR}" = true ]     && OPTIONAL_PROFILES="${OPTIONAL_PROFILES} --asr"

cat > "${PACKAGE_DIR}/install.sh" << INSTALL_SCRIPT
#!/bin/bash
# =============================================================================
# Yuxi-Know 客户现场安装脚本
#
# 本包包含的可选服务镜像: ${OPTIONAL_PROFILES:-无（仅基础服务）}
#
# 用法:
#   ./install.sh                           # 离线模式，从 tar 加载所有镜像
#   ./install.sh --online                  # 在线模式，第三方镜像从网络拉取
#   ./install.sh --ocr                     # 同时启动 MinerU OCR（需要 NVIDIA GPU）
#   ./install.sh --paddlex                 # 同时启动 PaddleX OCR（需要 NVIDIA GPU）
#   ./install.sh --asr                     # 同时启动 Whisper ASR（需要 NVIDIA GPU）
#   ./install.sh --ocr --paddlex --asr     # 启动所有可选服务
#   ./install.sh --all                     # 等同于上一条
#
# --online 模式说明:
#   自定义镜像 (yuxi-api, yuxi-web) 仍从 tar 加载（无公开仓库）
#   第三方镜像 (postgres, redis, neo4j 等) 从 Docker Hub 在线拉取
#   适合部署机器网络良好、希望减少传输包体积的场景
# =============================================================================

set -e

DEPLOY_OCR=false
DEPLOY_PADDLEX=false
DEPLOY_ASR=false
ONLINE_MODE=false

for arg in "\$@"; do
    case "\${arg}" in
        --ocr)     DEPLOY_OCR=true ;;
        --paddlex) DEPLOY_PADDLEX=true ;;
        --asr)     DEPLOY_ASR=true ;;
        --all)     DEPLOY_OCR=true; DEPLOY_PADDLEX=true; DEPLOY_ASR=true ;;
        --online)  ONLINE_MODE=true ;;
    esac
done

cd "\$(dirname "\${BASH_SOURCE[0]}")"

echo "======================================================"
echo "  Yuxi-Know 安装脚本"
echo "  安装模式  : \$([ "\${ONLINE_MODE}" = true ] && echo '在线' || echo '离线')"
echo "  MinerU OCR : \${DEPLOY_OCR}"
echo "  PaddleX OCR: \${DEPLOY_PADDLEX}"
echo "  Whisper ASR: \${DEPLOY_ASR}"
echo "======================================================"
echo ""

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo "[错误] 未检测到 Docker，请先安装 Docker Engine"
    echo "  参考: https://docs.docker.com/engine/install/"
    exit 1
fi
if ! docker compose version &> /dev/null; then
    echo "[错误] 未检测到 Docker Compose Plugin，请升级 Docker 到最新版"
    exit 1
fi

# ── 步骤 1：加载/拉取镜像 ────────────────────────────────
if [ "\${ONLINE_MODE}" = true ]; then
    # ── 在线模式：自定义镜像从 tar 加载，第三方镜像从网络拉取 ──
    echo "[1/3] 加载自定义镜像..."
    BASE_TAR=\$(ls yuxi-know-*-base.tar 2>/dev/null | head -1)
    if [ -n "\${BASE_TAR}" ]; then
        docker load -i "\${BASE_TAR}"
        echo "  自定义镜像加载完成"
    else
        echo "[错误] 未找到 yuxi-know-*-base.tar（自定义镜像必须从 tar 加载）"
        exit 1
    fi

    echo "[1/3] 在线拉取第三方镜像..."
    THIRD_PARTY_IMAGES=(
        "postgres:16"
        "redis:7-alpine"
        "neo4j:5.26"
        "quay.io/coreos/etcd:v3.5.5"
        "minio/minio:RELEASE.2023-03-20T20-16-18Z"
        "milvusdb/milvus:v2.5.6"
    )
    for img in "\${THIRD_PARTY_IMAGES[@]}"; do
        echo "  拉取 \${img}..."
        docker pull "\${img}"
    done

    if [ "\${DEPLOY_OCR}" = true ]; then
        TAR=\$(ls yuxi-know-*-ocr.tar 2>/dev/null | head -1)
        if [ -n "\${TAR}" ]; then
            docker load -i "\${TAR}" && echo "  MinerU OCR 镜像加载完成"
        else
            echo "[错误] 未找到 yuxi-know-*-ocr.tar（自定义镜像必须从 tar 加载）"
            exit 1
        fi
    fi

    if [ "\${DEPLOY_PADDLEX}" = true ]; then
        TAR=\$(ls yuxi-know-*-paddlex.tar 2>/dev/null | head -1)
        if [ -n "\${TAR}" ]; then
            docker load -i "\${TAR}" && echo "  PaddleX OCR 镜像加载完成"
        else
            echo "[错误] 未找到 yuxi-know-*-paddlex.tar（自定义镜像必须从 tar 加载）"
            exit 1
        fi
    fi

    if [ "\${DEPLOY_ASR}" = true ]; then
        echo "  拉取 fedirz/faster-whisper-server:latest-cuda..."
        docker pull "fedirz/faster-whisper-server:latest-cuda"
    fi
else
    # ── 离线模式：所有镜像从 tar 加载 ──
    echo "[1/3] 加载基础镜像..."
    BASE_TAR=\$(ls yuxi-know-*-base.tar 2>/dev/null | head -1)
    if [ -z "\${BASE_TAR}" ]; then
        echo "[错误] 未找到基础镜像包 yuxi-know-*-base.tar"
        exit 1
    fi
    docker load -i "\${BASE_TAR}"
    echo "  基础镜像加载完成"

    if [ "\${DEPLOY_OCR}" = true ]; then
        TAR=\$(ls yuxi-know-*-ocr.tar 2>/dev/null | head -1)
        [ -z "\${TAR}" ] && { echo "[错误] 未找到 yuxi-know-*-ocr.tar"; exit 1; }
        docker load -i "\${TAR}" && echo "  MinerU OCR 镜像加载完成"
    fi

    if [ "\${DEPLOY_PADDLEX}" = true ]; then
        TAR=\$(ls yuxi-know-*-paddlex.tar 2>/dev/null | head -1)
        [ -z "\${TAR}" ] && { echo "[错误] 未找到 yuxi-know-*-paddlex.tar"; exit 1; }
        docker load -i "\${TAR}" && echo "  PaddleX OCR 镜像加载完成"
    fi

    if [ "\${DEPLOY_ASR}" = true ]; then
        TAR=\$(ls yuxi-know-*-asr.tar 2>/dev/null | head -1)
        [ -z "\${TAR}" ] && { echo "[错误] 未找到 yuxi-know-*-asr.tar"; exit 1; }
        docker load -i "\${TAR}" && echo "  Whisper ASR 镜像加载完成"
    fi
fi

# ── 步骤 2：配置环境变量 ──────────────────────────────────
echo ""
echo "[2/3] 配置环境变量..."
if grep -q "^SILICONFLOW_API_KEY=\$" ".env.prod" 2>/dev/null; then
    echo ""
    echo "  ⚠️  请编辑 .env.prod，填入 LLM API Key 等配置"
    echo ""
    read -p "  是否现在编辑 .env.prod？[Y/n] " EDIT_ENV
    if [[ "\${EDIT_ENV}" != "n" && "\${EDIT_ENV}" != "N" ]]; then
        \${EDITOR:-vi} .env.prod
    fi
fi

# ── 步骤 3：启动服务 ──────────────────────────────────────
echo ""
echo "[3/3] 启动服务..."

PROFILES=""
[ "\${DEPLOY_OCR}" = true ]     && PROFILES="\${PROFILES} --profile ocr"
[ "\${DEPLOY_PADDLEX}" = true ] && PROFILES="\${PROFILES} --profile paddlex"
[ "\${DEPLOY_ASR}" = true ]     && PROFILES="\${PROFILES} --profile asr"

docker compose -f docker-compose.prod.yml \${PROFILES} up -d

echo ""
echo "======================================================"
echo "  安装完成！"
echo ""
echo "  Web 界面:  http://\$(hostname -I | awk '{print \$1}'):18080"
echo "  API 接口:  http://\$(hostname -I | awk '{print \$1}'):5050/docs"
echo ""
echo "  查看服务状态: docker compose -f docker-compose.prod.yml ps"
echo "  查看日志:     docker logs api-prod --tail 100"
echo "======================================================"
INSTALL_SCRIPT

chmod +x "${PACKAGE_DIR}/install.sh"

# ============================================================
# 第五步：输出摘要
# ============================================================
echo ""
echo "[5/5] 完成！"
echo ""
echo "======================================================"
echo "  部署包已生成: ${PACKAGE_DIR}/"
echo ""
echo "  包含文件:"
find "${PACKAGE_DIR}" -not -path "*/docker/volumes/*" -not -type d | sort | sed "s|${PACKAGE_DIR}/||"
echo ""
echo "  客户现场操作步骤:"
echo "  1. 将 ${PACKAGE_DIR}/ 整个目录拷贝到目标服务器"
echo "  2. cd deploy-package"
echo "  3. ./install.sh                       # 基础部署"
[ "${BUILD_OCR}" = true ]     && echo "     ./install.sh --ocr                 # 含 MinerU OCR"
[ "${BUILD_PADDLEX}" = true ] && echo "     ./install.sh --paddlex             # 含 PaddleX OCR"
[ "${BUILD_ASR}" = true ]     && echo "     ./install.sh --asr                 # 含 Whisper ASR"
[ "${BUILD_OCR}" = true ] && [ "${BUILD_PADDLEX}" = true ] && [ "${BUILD_ASR}" = true ] && \
    echo "     ./install.sh --all               # 全部可选服务"
echo "======================================================"
