import time
import redis
import json
from functools import wraps
import os


class NotCached(object):
    pass


class RedisLRUCache(object):
    def __init__(
        self, host="localhost", port=6379, db=0, max_size=10000, global_expire=None
    ):
        self.host = host
        self.port = port
        self.db = db
        self.max_size = max_size
        self.global_expire = global_expire
        self.redis = redis.Redis(host=self.host, port=self.port, db=self.db)

    def browse_cache(self, key, query):
        values = self.redis.lrange(key, 0, -1)
        for value in values:
            tmp = json.loads(value)
            dict_val = tuple(tmp.values())[0]
            if dict_val["expire"]:
                if dict_val["timestamp"] + dict_val["expire"] < time.time():
                    self.redis.lrem(key, 0, value)
                    continue
            if query in tmp:
                return tmp
        return {}

    def get(self, key, args, kwargs):
        input_args = {"args": list(args), "kwargs": kwargs}
        input_args_json = json.dumps(input_args)
        values = self.browse_cache(key, query=input_args_json)
        if input_args_json in values:
            return values[input_args_json]
        else:
            return NotCached

    def set(self, key, value):
        if self.redis.llen(key) >= self.max_size:
            self.redis.lpop(key)
        self.redis.rpush(key, value)
        if self.global_expire:
            self.redis.expire(key, self.global_expire)

    def delete(self, key):
        self.redis.delete(key)

    def clear(self):
        self.redis.flushdb()


def redis_lru(func=None, expire=None):
    cache = RedisLRUCache(max_size=os.environ.get("REDIS_LRU_CACHE_SIZE", 10000))

    def generate_key(func):
        return func.__name__

    def generate_value(func, *args, **kwargs):
        output = func(*args, **kwargs)
        key = json.dumps({"args": args, "kwargs": kwargs})
        return json.dumps(
            {key: {"output": output, "timestamp": time.time(), "expire": expire}}
        )

    def update_cache(key, val, *args, **kwargs):
        arg_key = json.dumps({"args": args, "kwargs": kwargs})
        data = json.dumps({arg_key: val})
        cache.redis.lrem(key, 0, data)
        cache.redis.rpush(key, data)

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = generate_key(func)
            value = cache.get(key, args, kwargs)
            if value != NotCached:
                print("cache hit")
                update_cache(key, value, *args, **kwargs)
                return value["output"]
            value_ = generate_value(func, *args, **kwargs)
            cache.set(key, value_)
            print("cache miss")
            return tuple(json.loads(value_).items())[0][1]["output"]

        return wrapper

    return decorator if func is None else decorator(func)


cache = RedisLRUCache(max_size=100)


@redis_lru(expire=100)
def fib(n):
    if n < 2:
        return 1
    return fib(n - 1) + fib(n - 2)


def fib_wo_cache(n):
    if n < 2:
        return 1
    return fib_wo_cache(n - 1) + fib_wo_cache(n - 2)


@redis_lru(expire=10)
def hello(name):
    import time

    time.sleep(3)
    return "Hello " + name


if __name__ == "__main__":
    prev_time = time.time()
    print(fib(10))
    print(time.time() - prev_time)
    prev_time = time.time()
    print(fib_wo_cache(10))
    print(time.time() - prev_time) # Issue: slow downs the program
    print(hello("World"))

    # time.sleep(10)
