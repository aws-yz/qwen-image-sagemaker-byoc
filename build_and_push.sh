#!/bin/bash
set -e

# 从 settings.json 读取配置
REGION=$(python3 -c "import json; print(json.load(open('settings.json'))['region'])")
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REPO_NAME=$(python3 -c "import json; print(json.load(open('settings.json'))['ecr_repo'])")
IMAGE_TAG="latest"
FULL_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${REPO_NAME}:${IMAGE_TAG}"

echo "Region: ${REGION}"
echo "Image:  ${FULL_URI}"

# 1. 登录 Base DLC ECR（拉取基础镜像）
echo "登录 Base DLC ECR..."
aws ecr get-login-password --region ${REGION} | \
    docker login --username AWS --password-stdin 763104351884.dkr.ecr.${REGION}.amazonaws.com

# 2. 创建 ECR 仓库（如不存在）
echo "创建 ECR 仓库..."
aws ecr describe-repositories --repository-names ${REPO_NAME} --region ${REGION} 2>/dev/null || \
    aws ecr create-repository --repository-name ${REPO_NAME} --region ${REGION}

# 3. 构建镜像
echo "构建 Docker 镜像..."
docker build -t ${REPO_NAME}:${IMAGE_TAG} .

# 4. 登录自己的 ECR
echo "登录自有 ECR..."
aws ecr get-login-password --region ${REGION} | \
    docker login --username AWS --password-stdin ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com

# 5. 推送
echo "推送镜像..."
docker tag ${REPO_NAME}:${IMAGE_TAG} ${FULL_URI}
docker push ${FULL_URI}

echo ""
echo "✅ 镜像已推送: ${FULL_URI}"
