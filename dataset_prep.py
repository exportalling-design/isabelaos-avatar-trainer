import os
from typing import List
from PIL import Image

def simple_prep(images: List[str], out_dir: str, max_side: int = 1024) -> List[str]:
    """
    Normaliza tamaño y guarda JPGs listos.
    Mantiene calidad alta; mínimo 768, máximo 1024 por lado.
    """
    os.makedirs(out_dir, exist_ok=True)
    out_files = []

    for path in images:
        img = Image.open(path).convert("RGB")
        w, h = img.size
        scale = min(max_side / max(w, h), 1.0)
        nw = int((w * scale) // 8 * 8)
        nh = int((h * scale) // 8 * 8)
        nw = max(nw, 768)
        nh = max(nh, 768)
        img = img.resize((nw, nh), Image.LANCZOS)

        out_path = os.path.join(out_dir, os.path.basename(path).rsplit(".", 1)[0] + ".jpg")
        img.save(out_path, "JPEG", quality=95)
        out_files.append(out_path)

    return out_files

def write_captions(image_paths: List[str], trigger: str):
    """
    Crea .txt por cada imagen con caption simple.
    """
    for ip in image_paths:
        txt = ip.rsplit(".", 1)[0] + ".txt"
        with open(txt, "w", encoding="utf-8") as f:
            f.write(f"{trigger}, person, portrait photo\n")
