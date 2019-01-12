import redis
import os


class Storage:
    conn = None

    def __init__(self):
        self.conn = redis.from_url(os.getenv('REDIS_URL', 'localhost'))

    def set(self, key, value):
        self.conn.set(key, value)

    def get(self, key):
        return self.conn.get(key)


cache = Storage()
