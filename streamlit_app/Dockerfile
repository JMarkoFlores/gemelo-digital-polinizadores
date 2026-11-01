FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-scientific.txt .
COPY streamlit_app/requirements.txt ./streamlit_requirements.txt
RUN pip install --no-cache-dir --default-timeout=1000 --retries 10 -r requirements-scientific.txt -r streamlit_requirements.txt

COPY scientific_core /app/scientific_core
COPY streamlit_app /app/streamlit_app
COPY configs /app/configs
COPY cli.py /app/cli.py

ENV PYTHONPATH=/app:/app/streamlit_app

EXPOSE 8501

WORKDIR /app/streamlit_app

CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
