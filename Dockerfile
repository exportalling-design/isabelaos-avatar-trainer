FROM pytorch/pytorch:2.3.1-cuda12.1-cudnn8-runtime

WORKDIR /app

# deps del sistema (git para HF, ffmpeg por si luego haces video, libgl por opencv)
RUN apt-get update && apt-get install -y \
  git \
  ffmpeg \
  libgl1 \
  libglib2.0-0 \
  && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Requirements
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# IMPORTANT: el script usa datasets + torchvision (no estaban en tu requirements)
RUN pip install --no-cache-dir \
  datasets==2.20.0 \
  torchvision==0.18.1 \
  huggingface_hub==0.24.6 \
  packaging==24.1 \
  tqdm==4.66.5 \
  einops==0.8.0

# Opcional: xformers para acelerar y reducir memoria (A100 lo soporta)
# Si te da problemas, comenta esta línea.
RUN pip install --no-cache-dir xformers==0.0.27.post2

# Copy code
COPY . /app

# sanity: asegúrate que tu script exista
RUN test -f /app/scripts/train_text_to_image_lora_sdxl.py

CMD ["python", "-u", "handler.py"]
