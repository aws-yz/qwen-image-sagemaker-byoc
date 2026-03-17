#!/usr/bin/env python3
"""
步骤 1：打包 Qwen-Image-2512 模型权重并上传 S3（BYOC 方案）
推理代码已在 Docker 镜像中，不打包 code/ 目录。
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


def prepare():
    if not os.path.exists(LOCAL_MODEL_DIR):
        print("❌ 模型目录不存在，请先运行 0_download_model.py")
        return

    tar_path = "model.tar.gz"
    s3_key = f"{S3_PREFIX}/model.tar.gz"
    model_data_url = f"s3://{S3_BUCKET}/{s3_key}"

    print(f"S3 目标: {model_data_url}")

    # 检查 S3 上是否已有模型
    s3 = boto3.client("s3", region_name=REGION)
    try:
        resp = s3.head_object(Bucket=S3_BUCKET, Key=s3_key)
        size_gb = resp["ContentLength"] / 1024**3
        print(f"\n⚠️  S3 上已存在模型 ({size_gb:.2f} GB)")
        if input("跳过上传? (y/n): ").lower() == "y":
            save_config(model_data_url)
            return
    except s3.exceptions.ClientError:
        pass

    print("\n📦 打包模型权重...")
    if os.path.exists(tar_path):
        os.remove(tar_path)

    cmd = f"tar --exclude='.cache' --exclude='code' -cf - -C {LOCAL_MODEL_DIR} . | pigz -p $(nproc) > {tar_path}"
    subprocess.run(cmd, shell=True, check=True)
    print(f"✓ 打包完成: {os.path.getsize(tar_path) / 1024**3:.2f} GB")

    print(f"\n📤 上传到 S3...")
    subprocess.run(
        f"aws s3 cp {tar_path} s3://{S3_BUCKET}/{s3_key} --region {REGION}",
        shell=True, check=True,
    )
    os.remove(tar_path)
    print(f"✓ 已上传: {model_data_url}")
    save_config(model_data_url)


def save_config(model_data_url):
    config = {
        "model_data_url": model_data_url,
        "s3_bucket": S3_BUCKET,
        "s3_prefix": S3_PREFIX,
        "region": REGION,
    }
    with open("config_2512.json", "w") as f:
        json.dump(config, f, indent=2)
    print("✓ 配置已保存: config_2512.json")


if __name__ == "__main__":
    prepare()
