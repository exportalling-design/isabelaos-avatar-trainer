import os
import json
import subprocess
from typing import Dict, Any

from config import HF_HOME, HF_HUB_CACHE, TRANSFORMERS_CACHE, DIFFUSERS_CACHE, TORCH_HOME, SDXL_BASE_ID

DIFFUSERS_SCRIPT_URL = (
    "https://raw.githubusercontent.com/huggingface/diffusers/main/examples/text_to_image/train_text_to_image_lora_sdxl.py"
)

def run_cmd(cmd: list, env: dict) -> None:
    p = subprocess.Popen(cmd, env=env)
    code = p.wait()
    if code != 0:
        raise RuntimeError(f"Training command failed with exit code {code}")

def _is_image(fn: str) -> bool:
    f = fn.lower()
    return f.endswith(".jpg") or f.endswith(".jpeg") or f.endswith(".png") or f.endswith(".webp")

def ensure_metadata_jsonl(dataset_dir: str, fallback_trigger: str) -> str:
    meta_path = os.path.join(dataset_dir, "metadata.jsonl")
    items = []

    for fn in sorted(os.listdir(dataset_dir)):
        if not _is_image(fn):
            continue

        img_path = os.path.join(dataset_dir, fn)
        txt_path = os.path.splitext(img_path)[0] + ".txt"

        caption = fallback_trigger
        if os.path.exists(txt_path):
            try:
                with open(txt_path, "r", encoding="utf-8") as f:
                    caption = (f.read() or "").strip() or fallback_trigger
            except Exception:
                caption = fallback_trigger

        items.append({"file_name": fn, "text": caption})

    if len(items) == 0:
        raise RuntimeError("Dataset is empty: no images found in dataset_dir")

    with open(meta_path, "w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")

    return meta_path

def ensure_diffusers_sdxl_script(local_dir: str) -> str:
    candidates = [
        "/app/scripts/train_text_to_image_lora_sdxl.py",
        "/app/train_text_to_image_lora_sdxl.py",
        os.path.join(local_dir, "scripts", "train_text_to_image_lora_sdxl.py"),
        os.path.join(local_dir, "train_text_to_image_lora_sdxl.py"),
    ]

    for candidate in candidates:
        if os.path.exists(candidate):
            print(f"[train_job] Using local SDXL script: {candidate}")
            return candidate

    tmp_path = "/tmp/train_text_to_image_lora_sdxl.py"
    if os.path.exists(tmp_path):
        print(f"[train_job] Using cached tmp SDXL script: {tmp_path}")
        return tmp_path

    has_curl = subprocess.call(["bash", "-lc", "command -v curl >/dev/null 2>&1"]) == 0
    has_wget = subprocess.call(["bash", "-lc", "command -v wget >/dev/null 2>&1"]) == 0

    if has_curl:
        cmd = ["bash", "-lc", f"curl -L --retry 3 -o {tmp_path} {DIFFUSERS_SCRIPT_URL}"]
    elif has_wget:
        cmd = ["bash", "-lc", f"wget -O {tmp_path} {DIFFUSERS_SCRIPT_URL}"]
    else:
        raise RuntimeError("Neither curl nor wget is available in container")

    code = subprocess.call(cmd)
    if code != 0 or not os.path.exists(tmp_path):
        raise RuntimeError("Could not download diffusers SDXL LoRA training script")

    print(f"[train_job] Downloaded SDXL script to: {tmp_path}")
    return tmp_path

def train_sdxl_lora(job: Dict[str, Any]) -> str:
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

    ensure_metadata_jsonl(dataset_dir, fallback_trigger=trigger)
    script = ensure_diffusers_sdxl_script(local_dir=os.path.dirname(__file__))

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
        "--output_dir", out_dir,
        "--checkpointing_steps", "0",
        "--validation_prompt", f"{trigger}, portrait photo",
        "--seed", "42",
    ]

    print(f"[train_job] Running script: {script}")
    run_cmd(cmd, env=env)

    candidates = []
    for fn in os.listdir(out_dir):
        if fn.endswith(".safetensors"):
            candidates.append(os.path.join(out_dir, fn))

    if candidates:
        candidates.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        return candidates[0]

    raise RuntimeError("No .safetensors produced in output_dir")
