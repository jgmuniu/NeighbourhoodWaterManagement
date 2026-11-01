FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt
COPY desktop /app/desktop
COPY backend /app/backend
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/backend/app:/app/desktop
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
