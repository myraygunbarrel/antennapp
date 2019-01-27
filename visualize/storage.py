import redis
from django.conf import settings


class Storage:
    conn = None
    session_time = 600

    def __init__(self):
        self.conn = redis.from_url(settings.REDIS_URL)

    def set(self, key, value):
        self.conn.set(key, value)
        self.conn.expire(key, self.session_time)

    def get(self, key):
        return self.conn.get(key)


cache = Storage()
