import time


class TokenBucket:
    def __init__(self, capacity, refill_per_second, clock=time.monotonic):
        if capacity <= 0 or refill_per_second <= 0:
            raise ValueError("capacity and refill rate must be positive")
        self.capacity, self.rate, self.clock = capacity, refill_per_second, clock
        self.tokens = float(capacity)
        self.last = clock()

    def allow(self, cost=1):
        now = self.clock()
        self.tokens = min(self.capacity, self.tokens + (now - self.last) * self.rate)
        self.last = now
        if self.tokens >= cost:
            self.tokens -= cost
            return True
        return False
