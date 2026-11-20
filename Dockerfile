FROM python:3.13-slim
WORKDIR /app
COPY RonahiBot.py prayers.json Bang-LICENSE.txt ./
CMD ["python", "-u", "RonahiBot.py"]
