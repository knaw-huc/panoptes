FROM python:3.13.3-bullseye AS python-base

# Set environment variables for Python, Pip, Poetry and project directories
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1 \
    PROJECT_DIR="/code"

# Add Poetry to the PATH
ENV PATH="$POETRY_HOME/bin:$PROJECT_DIR/.venv/bin:$PATH"

#FROM python-base AS production

# Install system dependencies
RUN buildDeps="build-essential" \
    && apt-get update \
    && apt-get install --no-install-recommends -y \
    curl \
    vim \
    netcat \
    && apt-get install -y --no-install-recommends $buildDeps \
    && rm -rf /var/lib/apt/lists/*

# Set Poetry and uv versions
ENV POETRY_VERSION=1.8.3
ENV UV_VERSION=0.2.17

# Install Poetry - respects $POETRY_VERSION & $POETRY_HOME
RUN curl -sSL https://install.python-poetry.org | python3 - && chmod a+x /opt/poetry/bin/poetry
RUN #poetry self add poetry-plugin-export
RUN pip install uv==$UV_VERSION

# Install package dependencies with uv
COPY poetry.lock pyproject.toml ./
RUN poetry export -f requirements.txt --output requirements.txt
RUN poetry run uv pip install -r requirements.txt

# Set working directory and copy package files
WORKDIR $PROJECT_DIR
ENV PATH="$POETRY_HOME/bin:$PROJECT_DIR/.venv/bin:$PATH"
COPY app ./app

EXPOSE 8000

# Set default command to run the application
ENTRYPOINT poetry run uvicorn app:app --port 8000 --host 0.0.0.0
