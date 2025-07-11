"""
Redis 연결 테스트 모듈
Redis 서버 연결 상태를 확인하고 테스트하는 기능을 제공합니다.
"""
from django.core.cache import cache
from django.conf import settings


def test_redis_connection() -> bool:
    """
    Redis 연결을 테스트합니다.
    
    Returns:
        Redis 연결 성공 여부
    """
    try:
        # 간단한 테스트 키로 Redis 연결 확인
        test_key = "redis_connection_test"
        test_value = "test_value"
        
        cache.set(test_key, test_value, timeout=10)
        retrieved_value = cache.get(test_key)
        cache.delete(test_key)
        
        return retrieved_value == test_value
    except Exception as e:
        print(f"Redis 연결 테스트 실패: {e}")
        return False


def get_cache_backend_info() -> str:
    """
    현재 사용 중인 캐시 백엔드 정보를 반환합니다.
    
    Returns:
        캐시 백엔드 정보 문자열
    """
    cache_backend = settings.CACHES['default']['BACKEND']
    if 'redis' in cache_backend.lower():
        return f"Redis Cache ({cache_backend})"
    elif 'locmem' in cache_backend.lower():
        return f"Memory Cache ({cache_backend})"
    else:
        return f"Other Cache ({cache_backend})"


def check_redis_status() -> dict:
    """
    Redis 상태를 종합적으로 확인합니다.
    
    Returns:
        Redis 상태 정보 딕셔너리
    """
    status = {
        'backend': get_cache_backend_info(),
        'connection_test': test_redis_connection(),
        'settings': {
            'backend': settings.CACHES['default']['BACKEND'],
            'location': settings.CACHES['default'].get('LOCATION', 'N/A'),
            'timeout': settings.CACHES['default'].get('TIMEOUT', 'N/A'),
            'key_prefix': settings.CACHES['default'].get('KEY_PREFIX', 'N/A'),
        }
    }
    
    # Redis 옵션 정보 추가
    if 'OPTIONS' in settings.CACHES['default']:
        status['settings']['options'] = settings.CACHES['default']['OPTIONS']
    
    return status


def print_redis_status():
    """
    Redis 상태를 콘솔에 출력합니다.
    """
    status = check_redis_status()
    
    print("=" * 50)
    print("Redis 상태 확인")
    print("=" * 50)
    print(f"백엔드: {status['backend']}")
    print(f"연결 테스트: {'성공' if status['connection_test'] else '실패'}")
    print(f"설정:")
    for key, value in status['settings'].items():
        print(f"  {key}: {value}")
    print("=" * 50) 