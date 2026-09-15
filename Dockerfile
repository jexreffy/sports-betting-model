FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip

COPY pyproject.toml README.md ./
COPY src ./src
COPY reports ./reports

RUN pip install --no-cache-dir .

ENV SBM_DATA_DIR=/app/data
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["sbm", "serve", "--host", "0.0.0.0", "--port", "8000"]
