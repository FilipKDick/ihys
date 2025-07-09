FROM python:3.13-slim AS builder
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app
 RUN pip install --no-cache-dir --upgrade pip && \
     pip install uv
COPY pyproject.toml uv.lock /app/
RUN uv sync
ENV PATH="/app/.venv/bin:$PATH"

FROM builder AS dev
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

FROM builder AS prod
COPY . .
CMD ["uvicorn", "app.main:app", "--ho
st", "0.0.0.0", "--port", "8000"]