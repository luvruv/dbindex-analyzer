# ==============================================================================
# Dockerfile for DbIndex Analyzer
# ==============================================================================
# A Dockerfile contains instructions to package an application and its environment
# into a lightweight, standalone container image that runs consistently anywhere.
# ==============================================================================

# Step 1: Base Image
# Start from the official Python 3.11 lightweight Linux image.
# "slim" provides a minimal Debian environment with Python pre-installed,
# keeping the final container image size small and secure.
FROM python:3.11-slim

# Step 2: Set Working Directory
# Define /app as the default directory inside the container for all subsequent commands.
WORKDIR /app

# Step 3: Leverage Docker Layer Caching for Dependencies
# Copy only requirements.txt first. Docker caches each step as a layer.
# By copying requirements separately from application code, Docker will reuse
# the cached dependencies layer whenever your Python code changes,
# speeding up rebuilds significantly!
COPY requirements.txt .

# Step 4: Install Python Dependencies
# Install required packages (psycopg2-binary, pytest) listed in requirements.txt.
# --no-cache-dir tells pip not to save downloaded archive files inside the image,
# which keeps the Docker image lightweight.
RUN pip install --no-cache-dir -r requirements.txt

# Step 5: Copy Application Source Code
# Copy all remaining project files (scripts, packages, tests) from the host machine
# into the container's working directory (/app).
# Files listed in .dockerignore (e.g., venv, __pycache__) are automatically skipped.
COPY . .

# Step 6: Define Container Entrypoint
# Specify the default executable to run when the container starts.
# Using ENTRYPOINT allows users to pass CLI arguments directly to the container:
# e.g.: docker run --rm dbindex-analyzer --help
ENTRYPOINT ["python", "index_analyzer.py"]