import time


class TokenBucket:
    def __init__(self, capacity, refill_per_second, clock=time.monotonic):
        raise NotImplementedError
