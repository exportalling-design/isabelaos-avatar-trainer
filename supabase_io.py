import os
from typing import List, Optional
from supabase import create_client, Client

from config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_AVATAR_BUCKET

def get_sb() -> Client:
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

def download_objects(paths: List[str], out_dir: str) -> List[str]:
    """
    paths: rutas dentro del bucket, ej:
      avatars/user123/avt_1/photos/1.jpg
    """
    sb = get_sb()
    os.makedirs(out_dir, exist_ok=True)
    local_files = []

    for p in paths:
        data = sb.storage.from_(SUPABASE_AVATAR_BUCKET).download(p)
        fname = os.path.basename(p)
        local_path = os.path.join(out_dir, fname)
        with open(local_path, "wb") as f:
            f.write(data)
        local_files.append(local_path)

    return local_files

def upload_file(local_path: str, remote_path: str, content_type: str = "application/octet-stream") -> str:
    sb = get_sb()
    with open(local_path, "rb") as f:
        sb.storage.from_(SUPABASE_AVATAR_BUCKET).upload(
            path=remote_path,
            file=f,
            file_options={"content-type": content_type, "upsert": "true"},
        )
    # Devuelve path (vos después podés convertir a signed URL cuando lo consumas)
    return remote_path

def delete_objects(paths: List[str]) -> None:
    if not paths:
        return
    sb = get_sb()
    sb.storage.from_(SUPABASE_AVATAR_BUCKET).remove(paths)

def set_avatar_status_rpc(avatar_id: str, status: str, lora_path: Optional[str] = None, trigger: Optional[str] = None, error: Optional[str] = None):
    """
    Recomendado: crear una RPC en Supabase para actualizar el avatar.
    Si no querés RPC, lo podés hacer desde tu backend Vercel.
    Aquí lo dejo como placeholder para que lo conectes como ya manejás tus tablas.
    """
    # Si no tenés RPC, simplemente no uses esto y actualizá desde Vercel.
    return
