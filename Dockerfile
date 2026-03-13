FROM runpod/pytorch:2.1.0-py3.10-cuda12.1.1-devel

WORKDIR /app

# instalar utilidades necesarias
RUN apt-get update && apt-get install -y \
    git \
    wget \
    curl \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# instalar dependencias python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copiar código
COPY . .

CMD ["python", "handler.py"]
