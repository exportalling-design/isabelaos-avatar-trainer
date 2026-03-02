FROM pytorch/pytorch:2.3.1-cuda12.1-cudnn8-runtime

WORKDIR /app

# -----------------------------
# System deps
# -----------------------------
RUN apt-get update && apt-get install -y \
    git \
    ffmpeg \
    libgl1 \
    wget \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# -----------------------------
# Python deps
# -----------------------------
COPY requirements.txt /app/requirements.txt

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r /app/requirements.txt

# -----------------------------
# HuggingFace cache optimization
# (IMPORTANT for RunPod volume performance)
# -----------------------------
ENV HF_HOME=/runpod-volume/hf
ENV HF_HUB_CACHE=/runpod-volume/hf
ENV TRANSFORMERS_CACHE=/runpod-volume/hf
ENV DIFFUSERS_CACHE=/runpod-volume/hf
ENV TORCH_HOME=/runpod-volume/torch

RUN mkdir -p /runpod-volume/hf
RUN mkdir -p /runpod-volume/torch

# -----------------------------
# Copy app
# -----------------------------
COPY . /app

# -----------------------------
# Accelerate config (auto)
# -----------------------------
RUN accelerate config default

# -----------------------------
# Start handler
# -----------------------------
CMD ["python", "-u", "handler.py"]
