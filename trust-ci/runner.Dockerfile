ARG PYTHON_BASE_IMAGE
FROM ${PYTHON_BASE_IMAGE}

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
RUN python -m pip install --no-cache-dir ".[test]" \
        coverage==7.15.4 \
        ruff==0.16.2 \
        bandit==1.9.4 \
        tomli==2.4.1

USER 10001:10001
WORKDIR /workspace
CMD ["python3", "--version"]
