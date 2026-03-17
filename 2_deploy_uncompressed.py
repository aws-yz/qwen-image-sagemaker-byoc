#!/usr/bin/env python3
"""
部署 Qwen-Image-2512（方案B：Uncompressed S3）
使用 ModelDataSource + S3DataSource（CompressionType=None），免去解压步骤。
配合 1_prepare_model_uncompressed.py 使用。
"""
import json
import time
import boto3

with open("settings.json", "r") as f:
    settings = json.load(f)
with open("config_2512.json", "r") as f:
    config = json.load(f)

REGION = config["region"]
INSTANCE_TYPE = settings["instance_type"]

sm = boto3.client("sagemaker", region_name=REGION)
account_id = boto3.client("sts", region_name=REGION).get_caller_identity()["Account"]
ECR_IMAGE = f"{account_id}.dkr.ecr.{REGION}.amazonaws.com/{settings['ecr_repo']}:latest"

ts = time.strftime("%m%d-%H%M")
NAME = f"qwen-image-2512-g7e-{ts}"

MODEL_S3URI = config.get("model_data_s3uri", "")


def deploy():
    print("=" * 60)
    print("Qwen-Image-2512 g7e BYOC 部署 (Uncompressed)")
    print("=" * 60)
    print(f"  镜像: {ECR_IMAGE}")
    print(f"  模型: {MODEL_S3URI}")
    print(f"  模式: Uncompressed S3")
    print(f"  实例: {INSTANCE_TYPE}")
    print(f"  名称: {NAME}")

    if not MODEL_S3URI:
        print("❌ config_2512.json 不是 uncompressed 方案，请先运行 1_prepare_model_uncompressed.py")
        return

    container = {
        "Image": ECR_IMAGE,
        "ModelDataSource": {
            "S3DataSource": {
                "S3Uri": MODEL_S3URI,
                "S3DataType": "S3Prefix",
                "CompressionType": "None",
            }
        },
    }

    sm.create_model(
        ModelName=NAME,
        PrimaryContainer=container,
        ExecutionRoleArn=f"arn:aws:iam::{account_id}:role/SageMakerExecutionRole",
    )
    print("✓ 模型已创建")

    sm.create_endpoint_config(
        EndpointConfigName=NAME,
        ProductionVariants=[{
            "VariantName": "AllTraffic",
            "ModelName": NAME,
            "InitialInstanceCount": 1,
            "InstanceType": INSTANCE_TYPE,
            "InitialVariantWeight": 1.0,
            "ContainerStartupHealthCheckTimeoutInSeconds": 1200,
        }],
    )
    print("✓ 端点配置已创建")

    sm.create_endpoint(EndpointName=NAME, EndpointConfigName=NAME)
    print(f"✓ 端点创建中: {NAME}")

    print("\n⏳ 等待端点就绪...")
    while True:
        resp = sm.describe_endpoint(EndpointName=NAME)
        status = resp["EndpointStatus"]
        print(f"  {time.strftime('%H:%M:%S')} {status}")
        if status == "InService":
            break
        if status == "Failed":
            print(f"❌ 失败: {resp.get('FailureReason', 'unknown')}")
            return
        time.sleep(30)

    print(f"\n✅ 端点就绪: {NAME}")

    with open("deploy_info.json", "w") as f:
        json.dump({
            "endpoint_name": NAME,
            "model_name": NAME,
            "endpoint_config_name": NAME,
            "region": REGION,
            "instance_type": INSTANCE_TYPE,
        }, f, indent=2)
    print("✓ deploy_info.json 已保存")


if __name__ == "__main__":
    confirm = input("确认部署? (y/n): ")
    if confirm.lower() == "y":
        deploy()
