# Dockerfile — IsabelaOS Comercial Assembler Worker
# Base: Python 3.11 slim con FFmpeg instalado
FROM python:3.11-slim
 
# Instalar FFmpeg y dependencias del sistema
RUN apt-get update && apt-get install -y \
    ffmpeg \
    ffprobe \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
 
# Verificar instalación de FFmpeg
RUN ffmpeg -version && ffprobe -version
 
# Directorio de trabajo
WORKDIR /app
 
# Copiar dependencias primero (para cache de Docker layers)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
 
# Copiar código del worker
COPY handler.py .
 
# Variable de entorno para RunPod
ENV PYTHONUNBUFFERED=1
 
# Comando de inicio
CMD ["python", "-u", "handler.py"]
