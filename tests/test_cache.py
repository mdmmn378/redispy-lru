import time
from redispy_lru.cache import redis_lru


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
    time.sleep(3)
    return "Hello " + name


def test_cache():
    start_time = time.time()
    print(fib(200))
    end_time = time.time()
    diff1 = end_time - start_time

    start_time = time.time()
    print(fib(200))
    end_time = time.time()
    diff2 = end_time - start_time

    print(diff1, diff2)
    assert diff2 < diff1
