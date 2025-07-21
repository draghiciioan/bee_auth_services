FROM python:3.12-slim

WORKDIR /app

# Instalează dependencies pentru Poetry
RUN pip install poetry

# Copiază fișierele Poetry
COPY pyproject.toml poetry.lock ./

# Configurează Poetry să nu creeze virtual environment
RUN poetry config virtualenvs.create false

# Instalează dependințele (sintaxa corectă pentru Poetry 2.x)
RUN poetry install --only=main --no-root

# Copiază codul aplicației
COPY . .

EXPOSE 8000

# Rulează aplicația
CMD ["poetry", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]