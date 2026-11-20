FROM python:3.13-slim
WORKDIR /app
COPY RonahiBot.py .
USER nobody
CMD ["python", "-u", "RonahiBot.py"]
