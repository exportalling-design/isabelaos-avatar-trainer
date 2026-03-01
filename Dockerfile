FROM runpod/pytorch:2.3.1-py3.10-cuda12.1.1-devel

WORKDIR /app

# system deps
RUN apt-get update && apt-get install -y git ffmpeg libgl1 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

# Importante: runpod serverless busca el handler
CMD ["python", "-u", "rp_train_handler.py"]
