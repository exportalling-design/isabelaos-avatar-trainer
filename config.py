import os

BASE_VOLUME = os.environ.get("BASE_VOLUME", "/runpod/volumes/isabelaos")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_AVATAR_BUCKET = os.environ.get("SUPABASE_AVATAR_BUCKET", "avatars")

SDXL_BASE_ID = os.environ.get("SDXL_BASE_ID", "stabilityai/stable-diffusion-xl-base-1.0")

DELETE_TRAINING_PHOTOS = str(os.environ.get("DELETE_TRAINING_PHOTOS", "true")).lower() == "true"

# Cache dirs (muy importante para que no re-descargue)
HF_HOME = f"{BASE_VOLUME}/huggingface"
HF_HUB_CACHE = f"{BASE_VOLUME}/huggingface/hub"
TRANSFORMERS_CACHE = f"{BASE_VOLUME}/huggingface/transformers"
DIFFUSERS_CACHE = f"{BASE_VOLUME}/huggingface/diffusers"
TORCH_HOME = f"{BASE_VOLUME}/torch"
