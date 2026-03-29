# Dockerfile — IsabelaOS Comercial Assembler Worker
# Usa jrottenberg/ffmpeg como base — FFmpeg ya incluido, sin apt-get
FROM jrottenberg/ffmpeg:4.4-ubuntu2004

# Instalar Python 3.11
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-distutils \
    python3-pip \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Hacer python3.11 el default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1

# Verificar
RUN python --version && ffmpeg -version

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY handler.py .

ENV PYTHONUNBUFFERED=1

CMD ["python", "-u", "handler.py"]
