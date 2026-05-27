# --- STAGE 1: COMPILATION & TEST GATE ---
FROM python:3.11-slim AS builder

WORKDIR /build

# Install dependencies needed for compiling package wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first to leverage Docker's caching layer
COPY requirements.txt .
RUN pip install --no-cache-dir --target=/build/deps -r requirements.txt

# Copy source and tests
COPY app/ ./app
COPY tests/ ./tests

# Configure python path to execute tests within the dependency folder
ENV PYTHONPATH=/build:/build/deps
# Run automated tests. If assertions fail, the build halts immediately.
RUN pip install pytest && python -m pytest -v tests/

# --- STAGE 2: PRODUCTION RUNTIME ENCAPSULATION ---
FROM python:3.11-slim AS runner

WORKDIR /app

# Create a non-privileged system user/group to prevent container escape exploits
RUN groupadd -g 1000 appgroup && \
    useradd -u 1000 -g appgroup -m -s /sbin/nologin appuser

# Copy installed dependencies and source code from builder
COPY --from=builder /build/deps /usr/local/lib/python3.11/site-packages
COPY app/ ./app

# Ensure application files are owned by our non-root user
RUN chown -R appuser:appgroup /app

# Switch to the non-root user
USER appuser

EXPOSE 8000

ENV PORT=8000 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

ENTRYPOINT ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
