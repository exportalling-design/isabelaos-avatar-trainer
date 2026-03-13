import os
import json
import subprocess
from typing import Dict, Any

from config import (
    HF_HOME,
    HF_HUB_CACHE,
    TRANSFORMERS_CACHE,
    DIFFUSERS_CACHE,
    TORCH_HOME,
    SDXL_BASE_ID,
)

DIFFUSERS_SCRIPT_URL = (
    "https://raw.githubusercontent.com/huggingface/diffusers/main/examples/text_to_image/train_text_to_image_lora_sdxl.py"
)


def run_cmd(cmd: list, env: dict) -> None:
    print("[train_job] Running command:")
    print(" ".join(cmd))

    p = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    stdout, stderr = p.communicate()

    if stdout:
        print("[train_job][stdout]")
        print(stdout)

    if stderr:
        print("[train_job][stderr]")
        print(stderr)

    if p.returncode != 0:
        raise RuntimeError(
            f"Training command failed with exit code {p.returncode}\n"
            f"STDERR:\n{stderr}\n"
            f"STDOUT:\n{stdout}"
        )


def _is_image(fn: str) -> bool:
    f = fn.lower()
    return f.endswith(".jpg") or f.endswith(".jpeg") or f.endswith(".png") or f.endswith(".webp")


def ensure_metadata_jsonl(dataset_dir: str, fallback_trigger: str) -> str:
    """
    Crea metadata.jsonl para diffusers usando captions .txt si existen.
    Formato:
      {"file_name":"xxx.jpg","text":"caption"}
    """
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

    print(f"[train_job] metadata.jsonl created with {len(items)} items at {meta_path}")
    return meta_path


def ensure_diffusers_sdxl_script(local_dir: str) -> str:
    """
    Busca el script localmente; si no existe, lo descarga a /tmp.
    """
    candidates = [
        os.path.join(local_dir, "scripts", "train_text_to_image_lora_sdxl.py"),
        os.path.join(local_dir, "train_text_to_image_lora_sdxl.py"),
        "/app/scripts/train_text_to_image_lora_sdxl.py",
        "/app/train_text_to_image_lora_sdxl.py",
        "/tmp/train_text_to_image_lora_sdxl.py",
    ]

    for c in candidates:
        if os.path.exists(c):
            print(f"[train_job] Using local script: {c}")
            return c

    tmp_path = "/tmp/train_text_to_image_lora_sdxl.py"

    if subprocess.call(["bash", "-lc", "command -v curl >/dev/null 2>&1"]) == 0:
        cmd = ["bash", "-lc", f"curl -L --retry 3 -o {tmp_path} {DIFFUSERS_SCRIPT_URL}"]
    elif subprocess.call(["bash", "-lc", "command -v wget >/dev/null 2>&1"]) == 0:
        cmd = ["bash", "-lc", f"wget -O {tmp_path} {DIFFUSERS_SCRIPT_URL}"]
    else:
        raise RuntimeError("Neither curl nor wget is available to fetch diffusers script")

    code = subprocess.call(cmd)
    if code != 0 or not os.path.exists(tmp_path):
        raise RuntimeError("Could not download diffusers SDXL LoRA training script")

    print(f"[train_job] Downloaded script to: {tmp_path}")
    return tmp_path


def train_sdxl_lora(job: Dict[str, Any]) -> str:
    dataset_dir = job["dataset_dir"]
    out_dir = job["out_dir"]
    trigger = job["trigger"]

    steps = int(job.get("steps", 1200))
    lr = float(job.get("lr", 1e-4))
    rank = int(job.get("rank", 16))
    batch = int(job.get("batch", 1))
    grad_acc = int(job.get("grad_acc", 4))

    os.makedirs(out_dir, exist_ok=True)

    env = os.environ.copy()
    env["HF_HOME"] = HF_HOME
    env["HF_HUB_CACHE"] = HF_HUB_CACHE
    env["TRANSFORMERS_CACHE"] = TRANSFORMERS_CACHE
    env["DIFFUSERS_CACHE"] = DIFFUSERS_CACHE
    env["TORCH_HOME"] = TORCH_HOME

    # Para evitar prompts interactivos raros
    env["HF_HUB_DISABLE_TELEMETRY"] = "1"
    env["TOKENIZERS_PARALLELISM"] = "false"

    # 1) Crear metadata para imagefolder
    ensure_metadata_jsonl(dataset_dir, fallback_trigger=trigger)

    # 2) Obtener script
    script = ensure_diffusers_sdxl_script(local_dir=os.path.dirname(__file__))

    # 3) Ejecutar entrenamiento
    cmd = [
        "accelerate",
        "launch",
        "--mixed_precision=fp16",
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
        "none",
        "--dataloader_num_workers",
        "0",
        "--seed",
        "42",
    ]

    run_cmd(cmd, env=env)

    # 4) Buscar el .safetensors de salida
    candidates = []
    for fn in os.listdir(out_dir):
        if fn.endswith(".safetensors"):
            candidates.append(os.path.join(out_dir, fn))

    if candidates:
        candidates.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        best = candidates[0]
        print(f"[train_job] Found safetensors: {best}")
        return best

    raise RuntimeError("No .safetensors produced in output_dir")
