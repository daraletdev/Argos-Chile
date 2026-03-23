FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Dependencies
COPY pyproject.toml .
COPY README.md .
COPY src/ ./src/
RUN pip install --no-cache-dir .

COPY scripts/ ./scripts/
COPY app/ ./app/

EXPOSE 8501

ENTRYPOINT ["streamlit", "run", "app/main.py", "--server.port=8501", "--server.address=0.0.0.0"]