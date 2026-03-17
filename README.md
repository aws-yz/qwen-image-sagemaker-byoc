# Qwen-Image-2512 — SageMaker BYOC (g7e.4xlarge)

在 SageMaker `ml.g7e.4xlarge` 上部署 [Qwen/Qwen-Image-2512](https://huggingface.co/Qwen/Qwen-Image-2512) 文生图模型。

采用 BYOC（Bring Your Own Container）方案：自建 Docker 镜像 + Flask/Gunicorn 推理服务。

## 性能参考

| 分辨率 | 步数 | 耗时 | 每步 |
|---------|------|------|------|
| 1328×1328 | 50 | ~58s | ~1.16s |
| 1328×1328 | 40 | ~41s | ~1.02s |
| 1664×928 | 50 | ~47s | ~0.94s |

## 两种部署方案

| | 方案 A：压缩包 | 方案 B：免压缩 |
|---|---|---|
| 上传方式 | pigz 打包 tar.gz → `aws s3 cp` | `aws s3 sync` 直接上传原始文件 |
| S3 存储 | 单个 42 GB tar.gz | 原始文件（54 GB） |
| 部署方式 | `ModelDataUrl` | `ModelDataSource` (CompressionType=None) |
| 启动时 | 需解压 tar.gz | 直接下载，无需解压 |
| 磁盘需求 | ≥ 100 GB（模型+压缩包） | ≥ 54 GB（仅模型） |
| 脚本 | `1_prepare_model.py` → `2_deploy.py` | `1_prepare_model_uncompressed.py` → `2_deploy_uncompressed.py` |

### 端点启动时间实测（Qwen-Image-2512, 54 GB, ml.g7e.4xlarge）

| 部署 | 总时间 | 容器启动前（S3→实例） |
|---|---|---|
| 方案 A | 10.5 分钟 | ~9.7 分钟 |
| 方案 B（第1次） | 27.6 分钟 | ~26.6 分钟（异常，疑似实例分配排队） |
| 方案 B（第2次） | 7.0 分钟 | ~5.8 分钟 |
| 方案 B（第3次） | 6.5 分钟 | ~5.9 分钟 |

方案 B 正常情况下比方案 A 快约 36%（~6.75 vs 10.5 分钟），因为跳过了 tar.gz 解压步骤。
推理性能两者完全一致（模型加载后无差异）。

### 如何选择

AWS 官方推荐大模型使用 uncompressed 模式：

> "For large model inference, we recommend that you deploy uncompressed ML model."
> — [Deploy uncompressed ML models](https://docs.aws.amazon.com/sagemaker/latest/dg/large-model-inference-uncompressed.html)

| 场景 | 推荐方案 |
|---|---|
| 大模型（>50 GB） | 方案 B（uncompressed），启动更快，准备更简单 |
| 小模型 | 方案 A（tar.gz），通用性好 |
| 需要 Batch Transform / Serverless / Multi-Model | 方案 A（方案 B 不支持） |
| 频繁更新模型权重 | 方案 B，`aws s3 sync` 支持增量同步 |
| 进一步优化启动速度 | 方案 B + [Fast Model Loader](https://aws.amazon.com/blogs/machine-learning/introducing-fast-model-loader-in-sagemaker-inference/)（LMI 容器，S3 直接流式传输到 GPU） |

参考文档：
- [S3ModelDataSource API](https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_S3ModelDataSource.html)
- [大模型推理端点参数](https://docs.aws.amazon.com/sagemaker/latest/dg/large-model-inference-hosting.html)
- [Fast Model Loader 博客](https://aws.amazon.com/blogs/machine-learning/introducing-fast-model-loader-in-sagemaker-inference-accelerate-autoscaling-for-your-large-language-models-llms-part-1/)

### CreateModel API 差异

方案 A — `ModelDataUrl`（传统方式，指向单个 tar.gz）：
```python
PrimaryContainer={
    "Image": ECR_IMAGE,
    "ModelDataUrl": "s3://bucket/prefix/model.tar.gz",
}
```

方案 B — `ModelDataSource`（免压缩，指向 S3 前缀）：
```python
PrimaryContainer={
    "Image": ECR_IMAGE,
    "ModelDataSource": {
        "S3DataSource": {
            "S3Uri": "s3://bucket/prefix/uncompressed/",  # 必须以 / 结尾
            "S3DataType": "S3Prefix",
            "CompressionType": "None",
        }
    },
}
```

> `ModelDataUrl` 和 `ModelDataSource` 二选一，不能同时指定。
> 方案 B 不支持 Batch Transform、Serverless Inference、Multi-model Endpoint。

## 目录结构

```
g7e-byoc/
├── settings.json                       # 配置（模型ID、区域、实例类型等）
├── Dockerfile                          # 基于 AWS DLC，安装 diffusers/transformers/gunicorn
├── serve.py                            # Flask + Gunicorn HTTP 服务（/ping, /invocations）
├── inference.py                        # 模型加载与推理逻辑
├── build_and_push.sh                   # 构建并推送 Docker 镜像到 ECR
├── 0_download_model.py                 # 下载模型到本地
├── 1_prepare_model.py                  # [方案A] 打包 tar.gz 并上传 S3
├── 1_prepare_model_uncompressed.py     # [方案B] 直接同步文件到 S3
├── 2_deploy.py                         # [方案A] 部署（ModelDataUrl）
├── 2_deploy_uncompressed.py            # [方案B] 部署（ModelDataSource）
├── 3_test.py                           # 测试推理（通用）
└── 4_cleanup.py                        # 清理资源（通用）
```

## 快速开始

### 1. 配置

编辑 `settings.json`：

```json
{
  "model_id": "Qwen/Qwen-Image-2512",
  "model_dir": "../model-2512",
  "region": "us-east-1",
  "s3_prefix": "models/qwen-image-2512",
  "ecr_repo": "qwen-image-g7e",
  "instance_type": "ml.g7e.4xlarge"
}
```

### 2. 下载模型

```bash
python 0_download_model.py
```

约 53.7 GB，支持断点续传。

### 3. 上传模型到 S3

方案 A（压缩包）：
```bash
python 1_prepare_model.py
```
使用 `pigz` 多核压缩 + `aws s3 cp` 多线程上传。

方案 B（免压缩，推荐）：
```bash
python 1_prepare_model_uncompressed.py
```
`aws s3 sync` 直接上传原始文件，省去压缩/解压步骤。

两者都会生成 `config_2512.json`。

### 4. 构建推送镜像

```bash
bash build_and_push.sh
```

自动登录 ECR、构建镜像、推送。

### 5. 部署端点

方案 A：
```bash
python 2_deploy.py
```

方案 B：
```bash
python 2_deploy_uncompressed.py
```

创建 SageMaker Model → EndpointConfig → Endpoint，等待 InService。生成 `deploy_info.json`。

### 6. 测试

```bash
python 3_test.py
```

### 7. 清理

```bash
python 4_cleanup.py
```

删除端点、端点配置、模型。

## 请求格式

```json
{
  "prompt": "一个咖啡店门口的黑板上写着'通义千问咖啡'",
  "negative_prompt": " ",
  "width": 1328,
  "height": 1328,
  "num_inference_steps": 50,
  "true_cfg_scale": 4.0,
  "seed": 42
}
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `prompt` | (必填) | 文本提示词 |
| `negative_prompt` | `" "` | 负面提示词 |
| `width` | 1328 | 图像宽度 |
| `height` | 1328 | 图像高度 |
| `num_inference_steps` | 50 | 推理步数，40 步可节省 ~20% 时间 |
| `true_cfg_scale` | 4.0 | CFG 引导强度 |
| `seed` | None | 随机种子，固定可复现 |

> 分辨率上限：`width × height ≤ 2048 × 2048`

## 响应格式

```json
{
  "image": "<base64 编码的 PNG>",
  "width": 1328,
  "height": 1328,
  "steps": 50
}
```

## 容器架构

```
Docker (BYOC)
├── 基础镜像: AWS DLC (CUDA 12.8, Python 3.12, Ubuntu 24.04)
├── 依赖: diffusers (git main), transformers 4.57.3, peft 0.17.1
├── serve.py → Gunicorn (1 worker, 1800s timeout)
│   ├── GET  /ping         → 健康检查，首次调用时加载模型
│   └── POST /invocations  → 推理请求
└── inference.py → DiffusionPipeline (bfloat16, full GPU)
```

## 前置条件

- AWS CLI 已配置，有 SageMaker / ECR / S3 权限
- Docker 已安装
- IAM 角色 `SageMakerExecutionRole` 已创建
- `ml.g7e.4xlarge` 配额充足（Service Quotas 中检查）
- 磁盘空间 ≥ 54 GB（方案 B）或 ≥ 100 GB（方案 A，模型 54 GB + 压缩包 43 GB）
