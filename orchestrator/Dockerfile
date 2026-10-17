FROM python:3.9-slim
WORKDIR /app
RUN pip install --no-cache-dir Flask==3.0.2 requests==2.31.0
COPY main.py .
EXPOSE 5000
CMD ["python", "main.py"]