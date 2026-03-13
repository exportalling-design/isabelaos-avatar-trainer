FROM pytorch/pytorch:2.3.1-cuda12.1-cudnn8-runtime

WORKDIR /app

RUN apt-get update && apt-get install -y \
    git \
    wget \
    curl \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip setuptools wheel

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

RUN pip install --no-cache-dir xformers==0.0.27.post2

COPY . /app

# aceptar script en /app/scripts o en /app raíz
RUN test -f /app/scripts/train_text_to_image_lora_sdxl.py || test -f /app/train_text_to_image_lora_sdxl.py

CMD ["python", "-u", "handler.py"]
