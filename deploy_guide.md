# Techave 勤怠管理システム  배포 가이드

## 🚀 추천 배포 플랫폼: Railway

### 1. Railway 계정 생성
1. [Railway.app](https://railway.app) 접속
2. GitHub 계정으로 로그인

### 2. 프로젝트 배포
1. **새 프로젝트 생성**
   - "Deploy from GitHub repo" 선택
   - GitHub 저장소 연결

2. **환경변수 설정**
   ```
   SECRET_KEY=your-secret-key-here
   DEBUG=False
   DJANGO_SETTINGS_MODULE=techave_kintai.settings_production
   ```

3. **데이터베이스 추가**
   - "New" → "Database" → "PostgreSQL" 선택
   - 자동으로 `DATABASE_URL` 환경변수 생성됨

4. **Redis 추가**
   - "New" → "Database" → "Redis" 선택
   - 자동으로 `REDIS_URL` 환경변수 생성됨

### 3. 도메인 설정
1. **Railway 도메인 사용**
   - 자동으로 `your-app.railway.app` 도메인 제공

2. **커스텀 도메인 연결**
   - Freenom에서 무료 도메인 획득 (예: `your-app.tk`)
   - Railway에서 커스텀 도메인 설정

## 🌐 무료 도메인 획득 방법

### Freenom 사용법
1. [Freenom.com](https://freenom.com) 접속
2. 원하는 도메인 검색 (`.tk`, `.ml`, `.ga`, `.cf`)
3. 무료로 등록 (12개월)
4. DNS 설정에서 Railway IP 연결

## 📋 배포 전 체크리스트

### 필수 파일 확인
- [x] `requirements.txt` - 의존성 패키지
- [x] `Procfile` - 배포 설정
- [x] `runtime.txt` - Python 버전
- [x] `techave_kintai/settings_production.py` - 프로덕션 설정

### 환경변수 설정
```
SECRET_KEY=your-secret-key-here
DEBUG=False
DJANGO_SETTINGS_MODULE=techave_kintai.settings_production
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
```

### 데이터베이스 마이그레이션
```bash
python manage.py migrate
python manage.py collectstatic --noinput
```

## 🔧 배포 후 설정

### 1. 슈퍼유저 생성
```bash
python manage.py createsuperuser
```

### 2. 초기 데이터 로드
```bash
python manage.py loaddata attendance/fixtures/holiday_calendar.json
```

### 3. 정적 파일 수집
```bash
python manage.py collectstatic --noinput
```

## 🛠️ 문제 해결

### 정적 파일 문제
- WhiteNoise 미들웨어 확인
- `STATIC_ROOT` 설정 확인

### 데이터베이스 연결 문제
- `DATABASE_URL` 환경변수 확인
- PostgreSQL 연결 테스트

### Redis 연결 문제
- `REDIS_URL` 환경변수 확인
- Redis 서비스 상태 확인

## 📞 지원

배포 중 문제가 발생하면:
1. Railway 로그 확인
2. Django 로그 확인
3. 환경변수 설정 재확인

## 💰 비용

### Railway 무료 티어
- 월 $5 크레딧 (충분함)
- PostgreSQL 무료
- Redis 무료
- 커스텀 도메인 지원

### Freenom 무료 도메인
- 12개월 무료
- 갱신 시 무료 (제한적) 