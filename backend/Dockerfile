FROM python:3.13-slim

# Install system dependencies and build tools
RUN apt-get update && apt-get install -y \
    postgresql-client \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Set working directory
WORKDIR /app

# Copy all source files first (needed for package detection)
COPY pyproject.toml uv.lock ./
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Install dependencies (package is now present for hatchling)
RUN uv sync --frozen --no-editable

# Copy entrypoint script
COPY entrypoint.sh ./
RUN chmod +x entrypoint.sh

# Use entrypoint script
ENTRYPOINT ["./entrypoint.sh"]
