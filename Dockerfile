# Python 3.11-slim-buster 이미지를 사용
FROM python:3.11-slim-buster

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 의존성 설치 (MySQL 클라이언트 라이브러리 등)
RUN apt-get update && apt-get install -y \
    default-libmysqlclient-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# requirements.txt만 먼저 복사하여 의존성 캐싱
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 프로젝트 전체 복사
COPY . .

# Django settings 모듈 환경변수 지정 (settings_production.py 사용)
ENV DJANGO_SETTINGS_MODULE=techave_kintai.settings_production

# Railway의 DATABASE_URL 환경변수 지정 (실제 배포시 Railway에서 자동 주입됨)
# 로컬 빌드/테스트용으로 아래 값 사용, 실제 배포시에는 Railway 대시보드에서 관리됨
ENV DATABASE_URL="mysql://root:NdNknbCgKKvdzMJcwbuPVfRwjoLGaNJQ@mysql-zbi2.railway.internal:3306/railway"

# 정적 파일 수집
RUN python manage.py collectstatic --noinput

# 컨테이너 실행 시 기본 명령 (Procfile이 있으면 생략 가능)
# CMD ["gunicorn", "techave_kintai.wsgi:application", "--bind", "0.0.0.0:$PORT"]
# 또는 start 스크립트가 있다면 아래처럼 사용
# CMD ["bash", "start"] 