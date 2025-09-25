import time
import threading
from collections import deque
from multiprocessing.managers import BaseManager
import logging

class RateLimiter:
    def __init__(self, requests_per_minute, seconds_per_request):
        self.requests_per_minute = requests_per_minute
        self.seconds_per_request = seconds_per_request
        self.request_timestamps = deque()
        self.request_queue = deque()
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self._process_queue, daemon=True)
        self.thread.start()
        logging.info(f"RateLimiter instance created: {id(self)}")

    def _process_queue(self):
        while True:
            if self.request_queue:
                time_to_wait = 0
                with self.lock:
                    now = time.time()
                    # Clean up old timestamps
                    while (self.request_timestamps and
                           now - self.request_timestamps[0] > 60):
                        self.request_timestamps.popleft()

                    if len(self.request_timestamps) >= self.requests_per_minute:
                        time_to_wait = 60 - (now - self.request_timestamps[0])

                if time_to_wait > 0:
                    logging.debug(f"Rate limit of {self.requests_per_minute}/minute reached. Waiting for {time_to_wait:.2f}s.")
                    time.sleep(time_to_wait)
                    continue # Re-evaluate after waiting

                # If we are here, we can process a request.
                with self.lock:
                    if not self.request_queue:
                        continue
                    request = self.request_queue.popleft()

                try:
                    logging.debug(f"RateLimiter {id(self)}: Processing request for {request['func'].__name__}")
                    result = request['func'](*request['args'], **request['kwargs'])
                    request['callback'](result)
                    with self.lock:
                        self.request_timestamps.append(time.time())

                except Exception as e:
                    request['callback'](e)

                time.sleep(self.seconds_per_request)
            else:
                time.sleep(0.1)

    def make_request(self, func, *args, **kwargs):
        logging.debug(f"RateLimiter {id(self)}: make_request called for {func.__name__}")
        callback_event = threading.Event()
        result = None
        error = None

        def callback(res):
            nonlocal result, error
            if isinstance(res, Exception):
                error = res
            else:
                result = res
            callback_event.set()

        with self.lock:
            self.request_queue.append({
                'func': func,
                'args': args,
                'kwargs': kwargs,
                'callback': callback
            })

        callback_event.wait()
        if error:
            raise error
        return result

class RateLimiterManager(BaseManager):
    pass

RateLimiterManager.register('RateLimiter', RateLimiter)

manager = RateLimiterManager()
manager.start()

coingecko_rate_limiter = manager.RateLimiter(requests_per_minute=8, seconds_per_request=1.11)