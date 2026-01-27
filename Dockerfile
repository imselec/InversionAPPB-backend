# Usa Python oficial
FROM python:3.11-slim

# Carpeta de trabajo
WORKDIR /app

# Instala dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo el código
COPY . .

# Comando para levantar FastAPI en el puerto que Render asigna
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT

