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

# 빌드 시점에 DJANGO_SETTINGS_MODULE 환경 변수 설정
ENV DJANGO_SETTINGS_MODULE=techave_kintai.settings_production

# 빌드 페이즈임을 알리는 환경 변수 설정 (DB 연결 회피용)
# ENV IS_BUILD_PHASE는 True 변수가 'True'이면 settings_production.py에서 인메모리 SQLite를 사용합니다.

# Railway의 DATABASE_URL을 명시적으로 Dockerfile에 설정합니다.
# IS_BUILD_PHASE가 True일 때는 이 값이 직접 사용되지 않지만,
# 최종 런타임 환경에서는 Railway가 제공하는 DATABASE_URL이 사용됩니다.
ENV DATABASE_URL="mysql://root:NdNknbCgKKvdzMJcwbuPVfRwjoLGaNJQ@mysql-zbi2.railway.internal:3306/railway"

# 정적 파일 수집
RUN python manage.py collectstatic --noinput

# 웹 서버 진입점 설정 (Procfile이 있다면 이 부분은 필요 없을 수 있습니다.)
CMD ["gunicorn", "techave_kintai.wsgi:application", "--bind", "0.0.0.0:$PORT"]
