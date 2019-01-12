import redis
import os
from django.conf import settings


class Storage:
    conn = None

    def __init__(self):
        self.conn = redis.from_url(settings.REDIS_URL)

    def set(self, key, value):
        self.conn.set(key, value)

    def get(self, key):
        return self.conn.get(key)


cache = Storage()
