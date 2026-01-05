# Stage 1: Builder
FROM python:3.10-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and build
COPY . .
RUN python3 build_solver.py

# Stage 2: Runtime
FROM python:3.10-slim

WORKDIR /app

# Install runtime libraries (OpenMP)
RUN apt-get update && apt-get install -y \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed dependencies from builder
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy compiled extension and app code
COPY --from=builder /app/thermal_solver_core.so .
COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]
