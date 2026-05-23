FROM python:3.11-slim

WORKDIR /project

RUN apt-get update && apt-get install -y \
    curl \
    espeak-ng \
    && rm -rf /var/lib/apt/lists/*

RUN pip install uv

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen

COPY app ./app

EXPOSE 8501

CMD ["uv", "run", "streamlit", "run", "app/main.py", "--server.address=0.0.0.0", "--server.port=8501"]