import os
import time
from typing import List, Optional

from supabase import Client, create_client

from config import (
    SUPABASE_URL,
    SUPABASE_SERVICE_ROLE_KEY,
    SUPABASE_AVATAR_BUCKET,
)


def get_sb() -> Client:

    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")

    return create_client(
        SUPABASE_URL,
        SUPABASE_SERVICE_ROLE_KEY
    )


def _normalize_storage_path(path: str) -> str:

    p = str(path or "").strip().lstrip("/")

    bucket_prefix = f"{SUPABASE_AVATAR_BUCKET}/"

    if p.startswith(bucket_prefix):
        p = p[len(bucket_prefix):]

    return p


def download_objects(paths: List[str], out_dir: str) -> List[str]:

    sb = get_sb()

    os.makedirs(out_dir, exist_ok=True)

    local_files = []

    for original_path in paths:

        normalized_path = _normalize_storage_path(original_path)

        fname = os.path.basename(normalized_path) or "file.bin"

        local_path = os.path.join(out_dir, fname)

        last_error = None

        for attempt in range(3):

            try:

                print(
                    f"[supabase_io] Downloading "
                    f"{normalized_path} "
                    f"attempt {attempt+1}/3"
                )

                data = sb.storage.from_(SUPABASE_AVATAR_BUCKET).download(
                    normalized_path
                )

                if data is None:
                    raise RuntimeError("Downloaded empty data")

                with open(local_path, "wb") as f:
                    f.write(data)

                local_files.append(local_path)

                print(f"[supabase_io] Saved {local_path}")

                last_error = None

                break

            except Exception as e:

                last_error = e

                print(
                    f"[supabase_io] Download failed "
                    f"{normalized_path} "
                    f"{repr(e)}"
                )

                if attempt < 2:
                    time.sleep(3)

        if last_error is not None:

            raise RuntimeError(
                f"Failed downloading {normalized_path} ({last_error})"
            )

    return local_files


def upload_file(
    local_path: str,
    remote_path: str,
    content_type: str = "application/octet-stream",
) -> str:

    sb = get_sb()

    normalized_remote = _normalize_storage_path(remote_path)

    print(
        f"[supabase_io] Uploading "
        f"{local_path} -> {normalized_remote}"
    )

    with open(local_path, "rb") as f:

        sb.storage.from_(SUPABASE_AVATAR_BUCKET).upload(
            path=normalized_remote,
            file=f,
            file_options={
                "content-type": content_type,
                "upsert": "true",
            },
        )

    return normalized_remote


def delete_objects(paths: List[str]) -> None:

    if not paths:
        return

    sb = get_sb()

    normalized = [_normalize_storage_path(p) for p in paths]

    print(f"[supabase_io] Deleting {normalized}")

    sb.storage.from_(SUPABASE_AVATAR_BUCKET).remove(normalized)


def set_avatar_status_rpc(
    avatar_id: str,
    status: str,
    lora_path: Optional[str] = None,
    trigger: Optional[str] = None,
    error: Optional[str] = None,
):
    return
