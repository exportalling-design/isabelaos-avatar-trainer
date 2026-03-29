# Dockerfile — IsabelaOS Comercial Assembler Worker
# Base oficial de RunPod — apt-get funciona correctamente en este entorno
FROM runpod/base:0.6.2-cuda12.1.0

# FFmpeg disponible en los repos de la imagen base de RunPod
RUN apt-get update && apt-get install -y ffmpeg && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY handler.py .

ENV PYTHONUNBUFFERED=1

CMD ["python3", "-u", "handler.py"]
