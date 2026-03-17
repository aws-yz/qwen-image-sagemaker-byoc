"""
极简 HTTP serving，替代 TorchServe。
SageMaker 要求容器监听 8080 端口，提供 /ping 和 /invocations。
"""
import os
import sys
import subprocess

from flask import Flask, request, Response

sys.path.insert(0, os.path.dirname(__file__))
from inference import model_fn, input_fn, predict_fn, output_fn

app = Flask(__name__)
model = None

MODEL_DIR = os.environ.get("SM_MODEL_DIR", "/opt/ml/model")


def _ensure_model():
    global model
    if model is None:
        print(f"加载模型: {MODEL_DIR}")
        model = model_fn(MODEL_DIR)
        print("✓ 模型加载完成")


@app.route("/ping", methods=["GET"])
def ping():
    _ensure_model()
    return Response(status=200 if model is not None else 503)


@app.route("/invocations", methods=["POST"])
def invocations():
    data = input_fn(request.get_data(), request.content_type or "application/json")
    result = predict_fn(data, model)
    output = output_fn(result, "application/json")
    return Response(output, mimetype="application/json")


if __name__ == "__main__":
    print("启动 gunicorn serving...")
    subprocess.run([
        sys.executable, "-m", "gunicorn", "serve:app",
        "-b", "0.0.0.0:8080",
        "-w", "1",
        "-t", "1800",
        "--chdir", os.path.dirname(__file__),
    ])
