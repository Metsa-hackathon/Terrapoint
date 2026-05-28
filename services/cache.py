import orjson


class CacheService:
    def __init__(self, redis_client):
        self.redis = redis_client

    async def get(self, key: str) -> dict | None:
        if not self.redis:
            return None
        try:
            raw = await self.redis.get(key)
            if raw is None:
                return None
            return orjson.loads(raw)
        except Exception:
            return None

    async def set(self, key: str, value: dict, ttl: int) -> bool:
        if not self.redis:
            return False
        try:
            data = orjson.dumps(value)
            await self.redis.set(key, data, ex=ttl)
            return True
        except Exception:
            return False

    async def delete(self, key: str) -> bool:
        if not self.redis:
            return False
        try:
            await self.redis.delete(key)
            return True
        except Exception:
            return False
