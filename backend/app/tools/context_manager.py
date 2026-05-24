import redis
import json
from app.config import get_settings

settings = get_settings()

class RedisContextManager:
    def __init__(self):
        self.redis = redis.from_url(settings.redis_url, decode_responses=True)

    def get_context(self, session_id: str):
        data = self.redis.get(f"chat:context:{session_id}")
        return json.loads(data) if data else {}

    def set_context(self, session_id: str, context: dict):
        self.redis.set(f"chat:context:{session_id}", json.dumps(context), ex=60*60*24)

    def get_history(self, session_id: str):
        data = self.redis.lrange(f"chat:history:{session_id}", 0, -1)
        return [json.loads(x) for x in data]

    def save_message(self, session_id: str, message: dict):
        self.redis.rpush(f"chat:history:{session_id}", json.dumps(message))
        self.redis.ltrim(f"chat:history:{session_id}", -20, -1)

    def clear(self, session_id: str):
        self.redis.delete(f"chat:context:{session_id}")
        self.redis.delete(f"chat:history:{session_id}")
