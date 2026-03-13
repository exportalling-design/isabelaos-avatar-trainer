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

RUN pip install --no-cache-dir \
    datasets==2.20.0 \
    torchvision==0.18.1 \
    huggingface_hub==0.24.6 \
    packaging==24.1 \
    tqdm==4.66.5 \
    einops==0.8.0 \
    xformers==0.0.27.post2

COPY . /app

CMD ["python", "-u", "handler.py"]
