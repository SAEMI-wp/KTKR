"""
社内の勤怠管理プロジェクト設定ファイル(techave_kintai/settings)。py)
目的:勤怠管理システムのDjangoフレームワーク設定管理
入出力: MySQL DB ↔ Django ORM, Redis Cache ↔ Session, Email ↔ SMTP
製作者: 権 セミ
作成日時: 2025.07.01
最後の修正日: 2025.07.15

主要構成:
- データベース接続(MySQL)
- セッション管理(Redis Cache)
- Eメール設定(SMTP)
- 静的ファイル管理
- セキュリティ設定
- 認証システム
"""
from pathlib import Path
import os
import pymysql
pymysql.install_as_MySQLdb()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY')
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
ALLOWED_HOSTS = ['*']

# Djangoアプリ設定
INSTALLED_APPS = [
    'django.contrib.admin',         # 管理ページ
    'django.contrib.auth',          # 認証システム
    'django.contrib.contenttypes',  # コンテンツタイプ
    'django.contrib.sessions',      # セッション管理
    'django.contrib.messages',      # メッセージフレームワーク
    'django.contrib.staticfiles',   # 静的ファイル管理
    'crispy_forms',                 # フォームレンダリング (attendance/forms.pyで使用)
    'crispy_bootstrap5',            # Bootstrap5 スタイル
    'attendance',                   # 勤怠管理メインアプリ
]

# ミドルウェア設定
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',           # セキュリティ·ヘッダー
    'django.contrib.sessions.middleware.SessionMiddleware',    # セッション処理
    'django.middleware.common.CommonMiddleware',               # 共通ミドルウェア
    'django.middleware.csrf.CsrfViewMiddleware',               # CSRF保護
    'django.contrib.auth.middleware.AuthenticationMiddleware', # 認証
    'django.contrib.messages.middleware.MessageMiddleware',    # メッセージ
    'django.middleware.clickjacking.XFrameOptionsMiddleware',  # クリックジャッキング防止
]

# プロジェクトのURLルーティングの開始点
ROOT_URLCONF = 'techave_kintai.urls'

# HTMLレンダリングエンジン
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'attendance', 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# WSGIサーバー用Django進入点
WSGI_APPLICATION = 'techave_kintai.wsgi.application'

# MySQL接続(attendance/models.py で使用)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ.get('DB_NAME'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST'),
        'PORT': os.environ.get('DB_PORT'),
        'OPTIONS': {
            'charset': 'utf8mb4',
        },
    }
}

# パスワード検証設定
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# カスタムユーザーモデル - attendance/models.py のEmployeeモデルを使用
AUTH_USER_MODEL = 'attendance.Employee'

# ログイン/ログアウト設定
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'

# 国際化設定
LANGUAGE_CODE = 'ja'
TIME_ZONE = 'Asia/Tokyo'
USE_I18N = True
USE_TZ = True

# 静的ファイル設定
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# X-Frame-Options設定(iframe許可)
X_FRAME_OPTIONS = 'SAMEORIGIN'

# Crispy Forms設定 - フォームレンダリング (attendance/forms.pyで使用)
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# メール設定
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST')
EMAIL_PORT = os.environ.get('EMAIL_PORT')
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'False').lower() == 'true'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# # Redisキャシュー設定
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL'),                        # Redisサーバーアドレス
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'PASSWORD': os.environ.get('REDIS_PASSWORD'),               # Redisパスワード
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,                                  # 最大接続数
                'retry_on_timeout': True,                               # タイムアウト時に再試行
            },
            'SOCKET_CONNECT_TIMEOUT': 5,                                # 連結タイムアウト
            'SOCKET_TIMEOUT': 5,                                        # ソケットタイムアウト
        },
        'TIMEOUT': 7200, 
        'KEY_PREFIX': 'techave_kintai',                                 # キャッシュキー接頭辞
    }
}

# キャッシュバックエンドでセッション保存
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

print("ALLOWED_HOSTS:", ALLOWED_HOSTS)
