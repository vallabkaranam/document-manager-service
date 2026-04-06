import os

from dotenv import load_dotenv
from redis import Redis
from redis.exceptions import RedisError

load_dotenv()

redis_url = os.getenv("REDIS_URL")

try:
    if redis_url:
        redis_client = Redis.from_url(redis_url, decode_responses=True)
    else:
        redis_client = Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            decode_responses=True,
        )
except RedisError:
    redis_client = None
