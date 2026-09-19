FROM python:3.11-slim-bookworm AS build

WORKDIR /build
COPY requirements.txt .
RUN python -m pip install --no-cache-dir --target=/install -r requirements.txt

FROM python:3.11-slim-bookworm AS runtime

RUN apt-get update \
    && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=build --chown=65532:65532 /install /app/site-packages
COPY --chown=65532:65532 . /app

ENV PYTHONPATH=/app/site-packages:/app \
    PYTHONUNBUFFERED=1 \
    PORT=8080

USER 65532:65532
EXPOSE 8080
ENTRYPOINT ["python3"]
CMD ["-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]

