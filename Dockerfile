FROM python:3.11-slim

WORKDIR /app

# Copiamos solo el contenido de backend
COPY . .

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Levantar uvicorn con host 0.0.0.0 y puerto de Render
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "$PORT"]
