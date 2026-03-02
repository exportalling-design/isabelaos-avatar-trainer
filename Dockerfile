FROM pytorch/pytorch:2.3.1-cuda12.1-cudnn8-runtime

WORKDIR /app

# deps del sistema (git para HF, ffmpeg por si luego haces video, libgl/libglib por opencv)
RUN apt-get update && apt-get install -y \
  git \
  ffmpeg \
  libgl1 \
  libglib2.0-0 \
  && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Requirements (TODO se controla aquí)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Opcional: xformers para acelerar y reducir memoria (A100 lo soporta)
# Si te da problemas de build, comenta esta línea.
RUN pip install --no-cache-dir xformers==0.0.27.post2

# Copy code
COPY . /app

# sanity: el script puede estar en /app/scripts o en /app directamente (según tu repo)
RUN test -f /app/scripts/train_text_to_image_lora_sdxl.py || test -f /app/train_text_to_image_lora_sdxl.py

CMD ["python", "-u", "handler.py"]
