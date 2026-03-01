import os
import subprocess
from typing import Dict, Any

from config import BASE_VOLUME, SDXL_BASE_ID, HF_HOME, HF_HUB_CACHE, TRANSFORMERS_CACHE, DIFFUSERS_CACHE, TORCH_HOME

def run_cmd(cmd: list, env: dict) -> None:
    p = subprocess.Popen(cmd, env=env)
    code = p.wait()
    if code != 0:
        raise RuntimeError(f"Training command failed with exit code {code}")

def train_sdxl_lora(job: Dict[str, Any]) -> str:
    """
    Entrena LoRA SDXL con script de diffusers (incluido por pip).
    Output: ruta local al .safetensors
    """
    dataset_dir = job["dataset_dir"]
    out_dir = job["out_dir"]
    trigger = job["trigger"]

    steps = int(job.get("steps", 1200))
    lr = float(job.get("lr", 1e-4))
    rank = int(job.get("rank", 16))
    alpha = int(job.get("alpha", 16))
    batch = int(job.get("batch", 1))
    grad_acc = int(job.get("grad_acc", 4))

    os.makedirs(out_dir, exist_ok=True)

    env = os.environ.copy()
    env["HF_HOME"] = HF_HOME
    env["HF_HUB_CACHE"] = HF_HUB_CACHE
    env["TRANSFORMERS_CACHE"] = TRANSFORMERS_CACHE
    env["DIFFUSERS_CACHE"] = DIFFUSERS_CACHE
    env["TORCH_HOME"] = TORCH_HOME

    # Script oficial diffusers (ya viene instalado con diffusers)
    # Nota: en algunas versiones la ruta cambia; este path suele funcionar:
    script = os.path.join(os.path.dirname(__file__), "scripts", "train_text_to_image_lora_sdxl.py")

    # Si no existe, usamos el que trae diffusers en site-packages
    if not os.path.exists(script):
        import diffusers
        base = os.path.dirname(diffusers.__file__)
        script = os.path.join(base, "examples", "text_to_image", "train_text_to_image_lora_sdxl.py")

    if not os.path.exists(script):
        raise RuntimeError("Could not find diffusers SDXL LoRA training script")

    cmd = [
        "accelerate", "launch",
        "--mixed_precision=fp16",
        script,
        "--pretrained_model_name_or_path", SDXL_BASE_ID,
        "--train_data_dir", dataset_dir,
        "--resolution", "1024",
        "--train_batch_size", str(batch),
        "--gradient_accumulation_steps", str(grad_acc),
        "--max_train_steps", str(steps),
        "--learning_rate", str(lr),
        "--rank", str(rank),
        "--lora_alpha", str(alpha),
        "--output_dir", out_dir,
        "--checkpointing_steps", "0",
        "--validation_prompt", f"{trigger}, portrait photo",
        "--seed", "42",
    ]

    run_cmd(cmd, env=env)

    # El script deja pesos en output_dir; buscamos el .safetensors
    for fn in os.listdir(out_dir):
        if fn.endswith(".safetensors"):
            return os.path.join(out_dir, fn)

    raise RuntimeError("No .safetensors produced in output_dir")
