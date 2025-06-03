FROM python:3.10-slim

WORKDIR /workspace

# 시스템 패키지 설치 (OpenCV 등 포함)
RUN apt-get update && apt-get install -y \
    g++ gcc libgdal-dev gdal-bin python3-dev \
    libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Python 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 코드 복사
COPY . .

# 기본 실행 명령
CMD ["python", "main.py"]
