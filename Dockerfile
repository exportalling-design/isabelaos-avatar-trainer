FROM pytorch/pytorch:2.3.1-cuda12.1-cudnn8-runtime

WORKDIR /app

# instalar deps del sistema PRIMERO (git necesario para pip)
RUN apt-get update && apt-get install -y \
    git \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# verificar git
RUN git --version

# actualizar pip
RUN python -m pip install --upgrade pip setuptools wheel

# copiar requirements
COPY requirements.txt .

# instalar python deps
RUN pip install --no-cache-dir -r requirements.txt

# xformers (acelera entrenamiento)
RUN pip install --no-cache-dir xformers==0.0.27.post2

# copiar código
COPY . .

# sanity check script
RUN ls -la /app
RUN test -f /app/scripts/train_text_to_image_lora_sdxl.py || true

CMD ["python", "-u", "handler.py"]
