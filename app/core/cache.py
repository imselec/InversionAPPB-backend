import time


class SimpleCache:

    def __init__(self, ttl=300):

        self.ttl = ttl
        self.data = {}

    def get(self, key):

        if key not in self.data:
            return None

        value, timestamp = self.data[key]

        if time.time() - timestamp > self.ttl:
            del self.data[key]
            return None

        return value

    def set(self, key, value):

        self.data[key] = (value, time.time())
