FROM python:3.12-slim

WORKDIR /app

# Install dependencies first for caching
COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir .

COPY . .

EXPOSE 8000
CMD ["bash", "start.sh"]
