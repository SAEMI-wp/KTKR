# 사용할 Python 버전과 기본 이미지 선택
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

# 임시 주석: 빌드 캐시를 무효화하기 위한 줄. 빌드 성공 후에는 삭제해도 됩니다.
RUN echo "Cache bust for tkinter fix"

# Python 출력 버퍼링 끄기 (로그가 즉시 출력되도록)
ENV PYTHONUNBUFFERED=1

# 빌드 시점에 DJANGO_SETTINGS_MODULE 환경 변수 설정
ENV DJANGO_SETTINGS_MODULE=techave_kintai.settings_production

# Railway의 DATABASE_URL을 명시적으로 Dockerfile에 설정합니다.
ENV DATABASE_URL="mysql://root:NdNknbCgKKvdzMJcwbuPVfRwjoLGaNJQ@mysql-zbi2.railway.internal:3306/railway"

# --- 디버깅 단계 추가 ---
# 1. 현재 작업 디렉토리의 파일 목록 확인
RUN echo "DEBUG: Listing files in /app:" && ls -l /app

# 2. techave_kintai 디렉토리의 파일 목록 확인 (settings_production.py와 __init__.py 확인용)
RUN echo "DEBUG: Listing files in /app/techave_kintai:" && ls -l /app/techave_kintai

# 3. manage.py 스크립트가 실행 가능한지 확인
RUN echo "DEBUG: Checking manage.py permissions:" && ls -l /app/manage.py

# 4. Django 설정 로딩 및 DATABASES 설정 확인
RUN echo "DEBUG: Attempting to load Django settings and print DATABASES config..." && \
    python -c "import os; import django; \
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'techave_kintai.settings_production'); \
    django.setup(); \
    from django.conf import settings; \
    print(f'DEBUG: settings.configured: {settings.configured}'); \
    print(f'DEBUG: settings.DATABASES: {settings.DATABASES}'); \
    if 'default' in settings.DATABASES and 'ENGINE' in settings.DATABASES['default']: \
        print(f'DEBUG: Default DB ENGINE: {settings.DATABASES['default']['ENGINE']}'); \
    else: \
        print('DEBUG: Default DB ENGINE or its ENGINE key is missing!');" 2>&1 | tee /dev/stderr

# 5. admin_views.py 파일 내용 출력 (매우 중요!)
# 이 명령을 통해 Railway 빌드 환경에서 실제로 사용되는 admin_views.py 파일의 내용을 확인합니다.
RUN echo "DEBUG: Content of /app/attendance/admin_views.py:" && cat /app/attendance/admin_views.py 2>&1 | tee /dev/stderr

# --- 정적 파일 수집 ---
RUN set -x && python -m django collectstatic --noinput 2>&1 | tee /dev/stderr

# 웹 서버 진입점 설정 (Procfile이 있다면 이 부분은 필요 없을 수 있습니다.)
CMD ["/bin/sh", "-c", "python manage.py migrate --noinput && gunicorn techave_kintai.wsgi:application --bind 0.0.0.0:$PORT"]
