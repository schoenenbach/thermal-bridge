FROM python:3.10-slim

# Install system dependencies for C++ compilation
RUN apt-get update && apt-get install -y \
    g++ \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Requirements first for cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Project Files
COPY . .

# Compile Solver
RUN python3 build_solver.py

# Expose Streamlit Port
EXPOSE 8501

# Run the Application
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]
