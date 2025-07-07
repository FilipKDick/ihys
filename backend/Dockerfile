FROM python:3.13-slim AS builder
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app
# RUN pip install --no-cache-dir --upgrade pip && \
#     pip install uv
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

FROM builder AS dev
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

FROM builder AS prod
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]