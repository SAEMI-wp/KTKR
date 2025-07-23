# 사용할 Python 버전과 기본 이미지 선택
# python:3.11-slim-buster 대신 python:3.11-slim-bullseye 사용
FROM python:3.11-slim-bullseye

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 의존성 설치 (MySQL 클라이언트 라이브러리)
RUN apt-get update && apt-get install -y \
    default-libmysqlclient-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# requirements.txt 복사 및 Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 프로젝트의 나머지 코드 복사
COPY . .

# 빌드 시점에 DJANGO_SETTINGS_MODULE 환경 변수 설정
ENV DJANGO_SETTINGS_MODULE=techave_kintai.settings_product

# Railway의 DATABASE_URL을 명시적으로 Dockerfile에 설정합니다.
ENV DATABASE_URL="mysql://root:NdNknbCgKKvdzMJcwbuPVfRwjoLGaNJQ@mysql-zbi2.railway.internal:3306/railway"

# 정적 파일 수집
RUN python manage.py collectstatic --noinput

# 웹 서버 진입점 설정 (Procfile이 있다면 이 부분은 필요 없을 수 있습니다.)
# CMD ["gunicorn", "techave_kintai.wsgi:application", "--bind", "0.0.0.0:$PORT"] 