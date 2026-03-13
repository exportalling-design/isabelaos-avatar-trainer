import os
from typing import List, Optional
from supabase import create_client, Client

from config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_AVATAR_BUCKET


def get_sb() -> Client:
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


def _normalize_storage_path(path: str) -> str:
    """
    El bucket se pasa aparte en .from_(bucket), así que aquí el path debe ir SIN el nombre del bucket.
    Ej:
      avatars/user123/x.jpg   -> user123/x.jpg   (si SUPABASE_AVATAR_BUCKET = avatars)
      /avatars/user123/x.jpg  -> user123/x.jpg
      user123/x.jpg           -> user123/x.jpg
    """
    p = str(path or "").strip().lstrip("/")
    bucket_prefix = f"{SUPABASE_AVATAR_BUCKET}/"

    if p.startswith(bucket_prefix):
        p = p[len(bucket_prefix):]

    return p


def download_objects(paths: List[str], out_dir: str) -> List[str]:
    """
    paths: rutas dentro del bucket o accidentalmente con prefijo del bucket.
    Ej válidos:
      user123/avt_1/train/1.jpg
      avatars/user123/avt_1/train/1.jpg
    """
    sb = get_sb()
    os.makedirs(out_dir, exist_ok=True)
    local_files = []

    for original_path in paths:
        normalized_path = _normalize_storage_path(original_path)

        print(f"[supabase_io] Downloading original='{original_path}' normalized='{normalized_path}' bucket='{SUPABASE_AVATAR_BUCKET}'")

        try:
            data = sb.storage.from_(SUPABASE_AVATAR_BUCKET).download(normalized_path)
        except Exception as e:
            print(f"[supabase_io] DOWNLOAD FAILED path='{normalized_path}' error={repr(e)}")
            raise RuntimeError(f"Failed to download storage object: {normalized_path} ({e})")

        if data is None:
            raise RuntimeError(f"Downloaded empty data from storage object: {normalized_path}")

        fname = os.path.basename(normalized_path) or "file.bin"
        local_path = os.path.join(out_dir, fname)

        with open(local_path, "wb") as f:
            f.write(data)

        local_files.append(local_path)
        print(f"[supabase_io] Saved local file: {local_path}")

    return local_files


def upload_file(local_path: str, remote_path: str, content_type: str = "application/octet-stream") -> str:
    sb = get_sb()
    normalized_remote = _normalize_storage_path(remote_path)

    print(f"[supabase_io] Uploading local='{local_path}' remote='{normalized_remote}' bucket='{SUPABASE_AVATAR_BUCKET}'")

    with open(local_path, "rb") as f:
        sb.storage.from_(SUPABASE_AVATAR_BUCKET).upload(
            path=normalized_remote,
            file=f,
            file_options={"content-type": content_type, "upsert": "true"},
        )

    return normalized_remote


def delete_objects(paths: List[str]) -> None:
    if not paths:
        return

    sb = get_sb()
    normalized = [_normalize_storage_path(p) for p in paths]

    print(f"[supabase_io] Deleting objects: {normalized}")
    sb.storage.from_(SUPABASE_AVATAR_BUCKET).remove(normalized)


def set_avatar_status_rpc(
    avatar_id: str,
    status: str,
    lora_path: Optional[str] = None,
    trigger: Optional[str] = None,
    error: Optional[str] = None,
):
    return
