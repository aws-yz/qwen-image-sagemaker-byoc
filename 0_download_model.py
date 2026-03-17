#!/usr/bin/env python3
"""
步骤 0：下载 Qwen-Image-2512 模型到本地
使用 huggingface_hub 下载，支持断点续传。
"""
import os
import json
import time
from huggingface_hub import snapshot_download

with open(os.path.join(os.path.dirname(__file__), "settings.json")) as f:
    _settings = json.load(f)

MODEL_ID = _settings["model_id"]
LOCAL_DIR = os.path.join(os.path.dirname(__file__), _settings["model_dir"])


def download():
    print("=" * 60)
    print(f"下载 {MODEL_ID}")
    print("=" * 60)
    print(f"  目标目录: {LOCAL_DIR}")

    t0 = time.time()
    snapshot_download(
        repo_id=MODEL_ID,
        local_dir=LOCAL_DIR,
        local_dir_use_symlinks=False,
    )
    elapsed = time.time() - t0

    # 统计
    total_size = 0
    file_count = 0
    for root, _, files in os.walk(LOCAL_DIR):
        for f in files:
            fp = os.path.join(root, f)
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)
                file_count += 1

    size_gb = total_size / 1024**3
    print(f"\n✅ 下载完成")
    print(f"  文件数: {file_count}")
    print(f"  总大小: {size_gb:.1f} GB")
    print(f"  耗时: {elapsed/60:.1f} 分钟")

    # 保存下载信息
    info = {
        "model_id": MODEL_ID,
        "local_dir": LOCAL_DIR,
        "model_size_gb": round(size_gb, 1),
        "file_count": file_count,
        "download_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "status": "completed",
    }
    info_path = os.path.join(os.path.dirname(__file__), "..", "model_download_info_2512.json")
    with open(info_path, "w") as f:
        json.dump(info, f, indent=2)
    print(f"  信息保存: {info_path}")


if __name__ == "__main__":
    download()
