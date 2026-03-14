import json
import os
import subprocess
from typing import Dict, Any

from config import (
    HF_HOME,
    HF_HUB_CACHE,
    TRANSFORMERS_CACHE,
    DIFFUSERS_CACHE,
    TORCH_HOME,
    SDXL_BASE_ID,
) my

DIFFUSERS_SCRIPT_URL = (
    "https://raw.githubusercontent.com/huggingface/diffusers/v0.29.2/examples/text_to_image/train_text_to_image_lora_sdxl.py"
)


def run_cmd(cmd: list, env: dict) -> None:
    p = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    stdout, stderr = p.communicate()

    print("STDOUT:")
    print(stdout or "")

    print("STDERR:")
    print(stderr or "")

    if p.returncode != 0:
        msg = f"Training command failed with exit code {p.returncode}"
        if stderr:
            msg += f"\nSTDERR:\n{stderr[-4000:]}"
        raise RuntimeError(msg)


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
        os.path.join(local_dir, "scripts", "train_text_to_image_lora_sdxl.py"),
        os.path.join(local_dir, "train_text_to_image_lora_sdxl.py"),
    ]

    for c in candidates:
        if os.path.exists(c):
            print(f"[train_job] Using local script: {c}")
            return c

    tmp_path = "/tmp/train_text_to_image_lora_sdxl.py"
    if os.path.exists(tmp_path):
        print(f"[train_job] Using cached tmp script: {tmp_path}")
        return tmp_path

    if subprocess.call(["bash", "-lc", "command -v curl >/dev/null 2>&1"]) == 0:
        cmd = ["bash", "-lc", f"curl -L --retry 3 -o {tmp_path} {DIFFUSERS_SCRIPT_URL}"]
    elif subprocess.call(["bash", "-lc", "command -v wget >/dev/null 2>&1"]) == 0:
        cmd = ["bash", "-lc", f"wget -O {tmp_path} {DIFFUSERS_SCRIPT_URL}"]
    else:
        raise RuntimeError("Neither curl nor wget is available to download training script")

    code = subprocess.call(cmd)
    if code != 0 or not os.path.exists(tmp_path):
        raise RuntimeError("Could not download diffusers SDXL LoRA training script")

    print(f"[train_job] Downloaded script to: {tmp_path}")
    return tmp_path


def train_sdxl_lora(job: Dict[str, Any]) -> str:
    dataset_dir = job["dataset_dir"]
    out_dir = job["out_dir"]
    trigger = job["trigger"]

    # ✅ Ajustados para que el archivo final tenga más chance de caber
    steps = int(job.get("steps", 800))
    lr = float(job.get("lr", 1e-4))
    rank = int(job.get("rank", 8))
    batch = int(job.get("batch", 1))
    grad_acc = int(job.get("grad_acc", 4))

    os.makedirs(out_dir, exist_ok=True)

    env = os.environ.copy()
    env["HF_HOME"] = HF_HOME
    env["HF_HUB_CACHE"] = HF_HUB_CACHE
    env["TRANSFORMERS_CACHE"] = TRANSFORMERS_CACHE
    env["DIFFUSERS_CACHE"] = DIFFUSERS_CACHE
    env["TORCH_HOME"] = TORCH_HOME

    try:
        import torch
        import torchvision
        import diffusers
        import transformers
        import accelerate

        print(f"[train_job] torch={torch.__version__}")
        print(f"[train_job] torchvision={torchvision.__version__}")
        print(f"[train_job] diffusers={diffusers.__version__}")
        print(f"[train_job] transformers={transformers.__version__}")
        print(f"[train_job] accelerate={accelerate.__version__}")
    except Exception as e:
        print(f"[train_job] Version log warning: {repr(e)}")

    ensure_metadata_jsonl(dataset_dir, fallback_trigger=trigger)
    script = ensure_diffusers_sdxl_script(local_dir=os.path.dirname(__file__))

    cmd = [
        "accelerate",
        "launch",
        "--mixed_precision=no",
        script,
        "--pretrained_model_name_or_path",
        SDXL_BASE_ID,
        "--train_data_dir",
        dataset_dir,
        "--resolution",
        "1024",
        "--train_batch_size",
        str(batch),
        "--gradient_accumulation_steps",
        str(grad_acc),
        "--max_train_steps",
        str(steps),
        "--learning_rate",
        str(lr),
        "--rank",
        str(rank),
        "--output_dir",
        out_dir,
        "--checkpointing_steps",
        "5000",
        "--validation_prompt",
        f"{trigger}, portrait photo",
        "--num_validation_images",
        "1",
        "--validation_epochs",
        "999999",
        "--report_to",
        "tensorboard",
        "--dataloader_num_workers",
        "0",
        "--seed",
        "42",
    ]

    print("[train_job] Running command:")
    print(" ".join(cmd))
    print(f"[train_job] Config -> steps={steps}, lr={lr}, rank={rank}, batch={batch}, grad_acc={grad_acc}")

    run_cmd(cmd, env=env)

    candidates = []
    for fn in os.listdir(out_dir):
        if fn.endswith(".safetensors"):
            full = os.path.join(out_dir, fn)
            size_mb = os.path.getsize(full) / (1024 * 1024)
            print(f"[train_job] Found output: {full} ({size_mb:.2f} MB)")
            candidates.append(full)

    if candidates:
        candidates.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        final_file = candidates[0]
        final_size_mb = os.path.getsize(final_file) / (1024 * 1024)
        print(f"[train_job] Final LoRA selected: {final_file} ({final_size_mb:.2f} MB)")
        return final_file

    raise RuntimeError("No .safetensors produced in output_dir")
