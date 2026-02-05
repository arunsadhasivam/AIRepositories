import json
from typing import Any, List, Optional
import redis 

class RedisRagCache:
    def __init__(self, url: str = "redis://localhost:6379", ttl_seconds: int = 0):
        self.r = redis.from_url(url)
        self.ttl = ttl_seconds

    def _key(self, query: str) -> str:
        norm = " ".join(query.lower().split())
        return f"rag_cache:{norm}"

    def get(self, query: str) -> Optional[dict]:
        data = self.r.get(self._key(query))
        return json.loads(data) if data else None

    def set(self, query: str, embedding: List[float], result: Any) -> None:
        value = json.dumps({"embedding": embedding, "result": result})
        key = self._key(query)
        if self.ttl > 0:
            self.r.setex(key, self.ttl, value)
        else:
            self.r.set(key, value)
