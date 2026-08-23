FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HOME=/home/ci

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates git php-cli composer nodejs npm \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 ci \
    && useradd --uid 10001 --gid 10001 --create-home --home-dir /home/ci ci

WORKDIR /opt/adaptive-trust-ci
COPY pyproject.toml README.md ./
COPY src ./src
RUN python -m pip install --no-cache-dir ".[test]" coverage ruff bandit

USER 10001:10001
WORKDIR /workspace
CMD ["python3", "--version"]
