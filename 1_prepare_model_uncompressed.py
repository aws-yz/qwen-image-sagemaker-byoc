#!/usr/bin/env python3
"""
步骤 1（方案B）：直接同步模型文件到 S3（无需打包压缩）
使用 aws s3 sync 上传原始文件，配合 2_deploy_uncompressed.py 部署。
"""
import json
import os
import subprocess
import boto3

with open("settings.json", "r") as f:
    settings = json.load(f)

REGION = settings["region"]
S3_PREFIX = settings["s3_prefix"]
LOCAL_MODEL_DIR = settings["model_dir"]

sts = boto3.client("sts", region_name=REGION)
account_id = sts.get_caller_identity()["Account"]
S3_BUCKET = f"sagemaker-{REGION}-{account_id}"
S3_URI = f"s3://{S3_BUCKET}/{S3_PREFIX}/uncompressed/"


def prepare():
    if not os.path.exists(LOCAL_MODEL_DIR):
        print("❌ 模型目录不存在，请先运行 0_download_model.py")
        return

    print(f"S3 目标: {S3_URI}")
    print(f"📤 同步模型文件到 S3...")
    subprocess.run(
        f"aws s3 sync {LOCAL_MODEL_DIR} {S3_URI} --region {REGION} --exclude '.cache/*'",
        shell=True, check=True,
    )
    print(f"✓ 同步完成: {S3_URI}")

    config = {
        "model_data_s3uri": S3_URI,
        "s3_bucket": S3_BUCKET,
        "s3_prefix": S3_PREFIX,
        "region": REGION,
        "compression": "None",
    }
    with open("config_2512.json", "w") as f:
        json.dump(config, f, indent=2)
    print("✓ 配置已保存: config_2512.json")


if __name__ == "__main__":
    prepare()
