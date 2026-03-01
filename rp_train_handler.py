import os
import traceback
from typing import Dict, Any

import runpod

from config import BASE_VOLUME, DELETE_TRAINING_PHOTOS
from supabase_io import download_objects, upload_file, delete_objects
from dataset_prep import simple_prep, write_captions
from train_job import train_sdxl_lora

def handler(event: Dict[str, Any]) -> Dict[str, Any]:
    try:
        input_data = event.get("input") or {}
        action = (input_data.get("action") or "").strip()
        if action != "avatar_train":
            return {"ok": False, "error": "INVALID_ACTION", "expected": "avatar_train"}

        avatar_id = (input_data.get("avatar_id") or "").strip()
        user_id = (input_data.get("user_id") or "").strip()
        trigger = (input_data.get("trigger") or "").strip()
        photo_paths = input_data.get("photos") or []

        if not avatar_id or not user_id or not trigger or not photo_paths:
            return {"ok": False, "error": "MISSING_FIELDS", "need": ["avatar_id", "user_id", "trigger", "photos[]"]}

        # Rutas en tu volume
        work_dir = f"{BASE_VOLUME}/avatars/{user_id}/{avatar_id}"
        raw_dir = f"{work_dir}/raw"
        dataset_dir = f"{work_dir}/dataset"
        out_dir = f"{work_dir}/lora_out"
        final_lora_local = f"{work_dir}/lora/avatar_lora.safetensors"
        final_lora_remote = f"avatars/{user_id}/{avatar_id}/lora/avatar_lora.safetensors"

        os.makedirs(work_dir, exist_ok=True)
        os.makedirs(raw_dir, exist_ok=True)
        os.makedirs(dataset_dir, exist_ok=True)
        os.makedirs(os.path.dirname(final_lora_local), exist_ok=True)

        # 1) Descargar fotos desde Supabase
        raw_files = download_objects(photo_paths, raw_dir)

        # 2) Preparar dataset + captions
        prepped = simple_prep(raw_files, dataset_dir, max_side=1024)
        write_captions(prepped, trigger)

        # 3) Entrenar LoRA SDXL
        lora_local_tmp = train_sdxl_lora({
            "dataset_dir": dataset_dir,
            "out_dir": out_dir,
            "trigger": trigger,
            "steps": input_data.get("steps", 1200),
            "lr": input_data.get("lr", 1e-4),
            "rank": input_data.get("lora_rank", 16),
            "alpha": input_data.get("lora_alpha", 16),
            "batch": input_data.get("batch", 1),
            "grad_acc": input_data.get("grad_acc", 4),
        })

        # Normalizamos el nombre final
        os.replace(lora_local_tmp, final_lora_local)

        # 4) Subir LoRA a Supabase Storage
        upload_file(final_lora_local, final_lora_remote, content_type="application/octet-stream")

        # 5) Borrar fotos originales (para ahorrar espacio)
        if DELETE_TRAINING_PHOTOS:
            delete_objects(photo_paths)

        return {
            "ok": True,
            "avatar_id": avatar_id,
            "user_id": user_id,
            "trigger": trigger,
            "lora_bucket_path": final_lora_remote,
            "deleted_training_photos": bool(DELETE_TRAINING_PHOTOS),
        }

    except Exception as e:
        print("[avatar_train ERROR]", repr(e))
        traceback.print_exc()
        return {"ok": False, "error": str(e)}

runpod.serverless.start({"handler": handler})
