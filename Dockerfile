# Dockerfile — IsabelaOS Comercial Assembler Worker
FROM runpod/base:0.6.2-cuda12.1.0

# Instalar FFmpeg
RUN apt-get update && apt-get install -y ffmpeg && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instalar runpod explícitamente primero
RUN pip install --no-cache-dir runpod==1.7.3

# Copiar y instalar requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY handler.py .

ENV PYTHONUNBUFFERED=1

CMD ["python3", "-u", "handler.py"]
