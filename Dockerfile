FROM runpod/pytorch:2.1.2-py3.10-cuda12.1.1-devel

WORKDIR /app

# deps del sistema (git es opcional, pero lo meto para evitar el warning)
RUN apt-get update && apt-get install -y git ffmpeg libgl1 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

CMD ["python", "-u", "handler.py"]
