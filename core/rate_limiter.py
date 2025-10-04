import time
import threading
from collections import deque
import logging

class RateLimiter:
    def __init__(self, requests_per_minute, seconds_per_request):
        self.requests_per_minute = requests_per_minute
        self.seconds_per_request = seconds_per_request
        self.request_timestamps = deque()
        self.request_queue = deque()
        self.lock = threading.Lock()
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"RateLimiter initialized with {requests_per_minute} req/min and {seconds_per_request}s/req.")
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

                    self.logger.debug(f"Rate limiter check: {len(self.request_timestamps)} requests in last 60s.")
                    if len(self.request_timestamps) >= self.requests_per_minute:
                        time_to_wait = 60 - (now - self.request_timestamps[0])
                        self.logger.warning(f"Rate limit reached ({len(self.request_timestamps)}/{self.requests_per_minute} req/min). Waiting for {time_to_wait:.2f}s.")

                if time_to_wait > 0:
                    time.sleep(time_to_wait)
                    continue # Re-evaluate after waiting

                # If we are here, we can process a request.
                with self.lock:
                    if not self.request_queue:
                        continue
                    request = self.request_queue.popleft()

                try:
                    self.logger.debug(f"RateLimiter {id(self)}: Processing request for {request['func'].__name__}")
                    result = request['func'](*request['args'], **request['kwargs'])
                    request['callback'](result)
                    with self.lock:
                        self.request_timestamps.append(time.time())
                    self.logger.debug(f"Request sent. Sleeping for {self.seconds_per_request}s.")

                except Exception as e:
                    request['callback'](e)

                time.sleep(self.seconds_per_request)
            else:
                time.sleep(0.1)

    def make_request(self, func, *args, **kwargs):
        logging.debug(f"RateLimiter {id(self)}: make_request called for {func.__name__}")
        callback_event = threading.Event() # Use threading.Event
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


_shared_rate_limiter = None

def get_shared_rate_limiter(requests_per_minute=7, seconds_per_request=1.11):
    global _shared_rate_limiter
    if _shared_rate_limiter is None:
        _shared_rate_limiter = RateLimiter(requests_per_minute=requests_per_minute, seconds_per_request=seconds_per_request)
    return _shared_rate_limiter

def shutdown_shared_rate_limiter():
    # No explicit shutdown needed for a thread-safe in-memory rate limiter
    pass