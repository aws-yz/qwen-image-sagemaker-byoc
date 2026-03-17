import json
import torch
import base64
import io
from diffusers import DiffusionPipeline


def model_fn(model_dir):
    pipe = DiffusionPipeline.from_pretrained(
        model_dir, torch_dtype=torch.bfloat16, local_files_only=True
    )
    pipe.to("cuda")
    print("✓ 模型已加载（全GPU模式，g7e）")
    return pipe


def input_fn(request_body, content_type):
    if content_type in ("application/json", "binary/octet-stream"):
        return json.loads(request_body)
    raise ValueError(f"不支持的 content type: {content_type}")


def predict_fn(input_data, model):
    try:
        prompt = input_data.get("prompt", "")
        negative_prompt = input_data.get("negative_prompt", " ")
        width = input_data.get("width", 1328)
        height = input_data.get("height", 1328)
        num_inference_steps = input_data.get("num_inference_steps", 50)
        seed = input_data.get("seed", None)
        true_cfg_scale = input_data.get("true_cfg_scale", 4.0)

        if width * height > 2048 * 2048:
            print(f"⚠️  分辨率 {width}x{height} 超出推荐上限 2048x2048")

        generator = None
        if seed is not None:
            generator = torch.Generator(device="cuda").manual_seed(seed)

        print(f"生成图像: {prompt[:50]}... ({width}x{height}, 步数: {num_inference_steps})")

        image = model(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            num_inference_steps=num_inference_steps,
            true_cfg_scale=true_cfg_scale,
            generator=generator,
        ).images[0]

        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode()

        print("✓ 图像生成完成")
        return {"image": img_base64, "width": width, "height": height, "steps": num_inference_steps}
    finally:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


def output_fn(prediction, accept):
    if accept == "application/json":
        return json.dumps(prediction)
    raise ValueError(f"不支持的 accept type: {accept}")
