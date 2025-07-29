from .settings import *  # 반드시 맨 위에!

import os
import dj_database_url
import pymysql
pymysql.install_as_MySQLdb()

# 빌드 시점임을 나타내는 환경 변수 확인
# Railway 배포 시에는 이 환경 변수가 설정되지 않으므로, 실제 DB 연결을 시도합니다.
IS_BUILD_PHASE = os.environ.get('IS_BUILD_PHASE', 'False').lower() == 'true'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-here')

# ALLOWED_HOSTS 설정
ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '.railway.app',
    '.render.com',
    '.herokuapp.com',
    '.pythonanywhere.com',
]

# CSRF 설정
CSRF_TRUSTED_ORIGINS = [
    'https://*.railway.app',
    'https://*.render.com',
    'https://*.herokuapp.com',
    'https://*.pythonanywhere.com',
]
# 환경 변수 값 확인용 코드 (배포 후 삭제)
_db_url_from_env = os.environ.get('DATABASE_URL')
# print(f"DEBUG: DATABASE_URL from environment: {_db_url_from_env}")

# 데이터베이스 설정 (환경 변수에서 가져오기)
if IS_BUILD_PHASE:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',  # 인메모리 SQLite 사용 (빌드 시에만)
        }
    }
else:
    # 런타임 환경 (IS_BUILD_PHASE가 False일 때)
    # Railway가 주입하는 DATABASE_URL 환경 변수를 명시적으로 가져옵니다.
    DATABASE_URL_FROM_RAILWAY = os.environ.get('DATABASE_URL')

    # 디버깅: DATABASE_URL 값이 제대로 읽히는지 확인 (로그에서 이 print 문을 찾아보세요!)
    print(f"DEBUG: Running in Runtime. IS_BUILD_PHASE={IS_BUILD_PHASE}")
    print(f"DEBUG: Retrieved DATABASE_URL from environment: {DATABASE_URL_FROM_RAILWAY}")

    if DATABASE_URL_FROM_RAILWAY:
        DATABASES = {
            'default': dj_database_url.config(
                default=DATABASE_URL_FROM_RAILWAY,
                conn_max_age=600,
                conn_health_checks=True,
            )
        }
        # 디버깅: 설정된 데이터베이스 엔진 확인 (로그에서 이 print 문을 찾아보세요!)
        print(f"DEBUG: Database configured with engine: {DATABASES['default']['ENGINE']}")
    else:
        # 프로덕션 환경에서 DATABASE_URL이 없을 경우 오류 발생
        # 이 부분이 실행되면 Railway Variables 설정을 다시 확인해야 합니다.
        from django.core.exceptions import ImproperlyConfigured
        raise ImproperlyConfigured("DATABASE_URL environment variable not set for production. Cannot connect to database.")

# 정적 파일 설정
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATIC_URL = '/static/'

# WhiteNoise 설정 (정적 파일 서빙)
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Redis 설정 (환경변수에서 가져오기)
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/1')
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
        },
        'TIMEOUT': 7200,
        'KEY_PREFIX': 'techave_kintai',
    }
}

# 세션 타임아웃 설정 (추가)
SESSION_COOKIE_AGE = 7200  # 30분 후 자동 로그아웃
SESSION_EXPIRE_AT_BROWSER_CLOSE = True  # 브라우저 닫으면 세션 만료 

SESSION_SAVE_EVERY_REQUEST = False  # 세션 만료 연장 방지
CACHES['default']['TIMEOUT'] = 7200  # Redis 캐시 만료 2시간
print("SESSION_COOKIE_AGE:", SESSION_COOKIE_AGE)
print("CACHES TIMEOUT:", CACHES['default']['TIMEOUT']) 

import datetime
print("서버 현재 시간:", datetime.datetime.now())
from django.utils import timezone
print("Django timezone.now():", timezone.now())
print("TIME_ZONE:", TIME_ZONE)
print("USE_TZ:", USE_TZ)
from django.utils import timezone
now = timezone.localtime()  # Asia/Tokyo 기준의 현재 시간
print("로컬 타임존 시간:", now) 

# 로깅 설정
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}

# 보안 설정
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True 
