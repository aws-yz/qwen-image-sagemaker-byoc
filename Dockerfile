FROM 763104351884.dkr.ecr.us-east-1.amazonaws.com/base:12.8.1-gpu-py312-cu128-ubuntu24.04-ec2

# pip 依赖
RUN pip install --no-cache-dir \
    torch --index-url https://download.pytorch.org/whl/cu128 && \
    pip install --no-cache-dir \
    flask \
    gunicorn \
    git+https://github.com/huggingface/diffusers.git \
    transformers==4.57.3 \
    peft==0.17.1 \
    Pillow \
    accelerate \
    safetensors \
    sentencepiece

# 推理代码
COPY serve.py /opt/ml/code/serve.py
COPY inference.py /opt/ml/code/inference.py

ENV SM_MODEL_DIR=/opt/ml/model
EXPOSE 8080

ENTRYPOINT ["python", "/opt/ml/code/serve.py"]
