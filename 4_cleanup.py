#!/usr/bin/env python3
"""
清理 Qwen-Image-2512 g7e BYOC 端点资源
"""
import json
import boto3

with open("deploy_info.json", "r") as f:
    info = json.load(f)

sm = boto3.client("sagemaker", region_name=info["region"])

print(f"将删除:")
print(f"  端点: {info['endpoint_name']}")
print(f"  配置: {info['endpoint_config_name']}")
print(f"  模型: {info['model_name']}")

if input("\n确认? (y/n): ").lower() != "y":
    print("已取消")
    exit()

for res_type, name in [
    ("endpoint", info["endpoint_name"]),
    ("endpoint_config", info["endpoint_config_name"]),
    ("model", info["model_name"]),
]:
    try:
        if res_type == "endpoint":
            sm.delete_endpoint(EndpointName=name)
        elif res_type == "endpoint_config":
            sm.delete_endpoint_config(EndpointConfigName=name)
        else:
            sm.delete_model(ModelName=name)
        print(f"✓ 已删除: {name}")
    except Exception as e:
        print(f"⚠️  {name}: {e}")

print("\n✅ 清理完成")
