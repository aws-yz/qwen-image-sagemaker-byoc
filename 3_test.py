#!/usr/bin/env python3
"""
测试 g7e BYOC 端点（同步推理）
"""
import json
import boto3
import base64
from datetime import datetime

with open("deploy_info.json", "r") as f:
    info = json.load(f)

ENDPOINT_NAME = info["endpoint_name"]
REGION = info["region"]
runtime = boto3.client("sagemaker-runtime", region_name=REGION)

test_cases = [
    {
        "name": "中文文本渲染",
        "payload": {
            "prompt": "一个咖啡店门口的黑板上写着'通义千问咖啡 ☕ 每杯2元', Ultra HD, 4K",
            "width": 1328, "height": 1328, "num_inference_steps": 50, "seed": 42,
        },
    },
    {
        "name": "英文文本渲染",
        "payload": {
            "prompt": "A coffee shop sign reading 'Qwen Coffee $2 per cup', Ultra HD, 4K",
            "width": 1664, "height": 928, "num_inference_steps": 50, "seed": 123,
        },
    },
]

for i, tc in enumerate(test_cases, 1):
    print(f"\n📝 测试 {i}: {tc['name']}")
    try:
        resp = runtime.invoke_endpoint(
            EndpointName=ENDPOINT_NAME,
            ContentType="application/json",
            Accept="application/json",
            Body=json.dumps(tc["payload"]),
        )
        result = json.loads(resp["Body"].read())
        img_data = base64.b64decode(result["image"])
        ts = datetime.now().strftime("%H%M%S")
        fname = f"output_{i}_{ts}.png"
        with open(fname, "wb") as f:
            f.write(img_data)
        print(f"✓ 已保存: {fname} ({result['width']}x{result['height']})")
    except Exception as e:
        print(f"❌ 失败: {e}")

print("\n✅ 测试完成")
