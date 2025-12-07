FROM python:3.11-slim AS build
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN apt-get update && apt-get install -y build-essential curl && rm -rf /var/lib/apt/lists/* 
RUN pip install --upgrade pip
RUN pip wheel --no-deps --wheel-dir /wheels -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
COPY --from=build /wheels /wheels
RUN pip install --no-index --find-links=/wheels -r /app/requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
