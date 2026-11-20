FROM python:3.13-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY ronahi_ai.py RonahiBot.py prayers.json Bang-LICENSE.txt ./
COPY web ./web
CMD ["python","-u","RonahiBot.py"]
