FROM runpod/pytorch:2.3.1-py3.10-cuda12.1.1-devel

WORKDIR /app

RUN apt-get update && apt-get install -y git ffmpeg libgl1 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# No pongas CMD aquí
