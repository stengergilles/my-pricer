import time
import threading
from collections import deque
import logging
import multiprocessing

from core.app_config import Config
from core.rate_limiter import RateLimiter # Import the simplified RateLimiter

def start_rate_limiter_process(request_queue: multiprocessing.Queue, response_queue: multiprocessing.Queue, config: Config):
    """
    Starts a dedicated process to manage the RateLimiter.
    All rate-limited requests are sent to this process via request_queue,
    and responses are sent back via response_queue.
    """
    logger = logging.getLogger(__name__)
    logger.info("Rate Limiter Process started.")

    # Instantiate the simplified RateLimiter
    rate_limiter = RateLimiter(
        requests_per_minute=config.COINGECKO_REQUESTS_PER_MINUTE,
        seconds_per_request=config.COINGECKO_SECONDS_PER_REQUEST
    )

    while True:
        try:
            # Get request from queue (blocking call)
            func_name, args, kwargs, request_id = request_queue.get()
            logger.debug(f"Rate Limiter Process: Received request {request_id} for {func_name}")

            def process_callback(result):
                response_queue.put((result, request_id))

            try:
                result = rate_limiter.make_request(func_name, *args, **kwargs)
                process_callback(result)
            except Exception as e:
                process_callback(e)

        except KeyboardInterrupt:
            logger.info("Rate Limiter Process received KeyboardInterrupt. Shutting down.")
            break
        except Exception as e:
            logger.error(f"Rate Limiter Process: An error occurred: {e}", exc_info=True)
            # If an error occurs, send it back to the caller
            response_queue.put((e, request_id))
            time.sleep(1) # Prevent busy-looping on continuous errors

if __name__ == '__main__':
    # This block is for testing the process independently
    # In actual use, it will be started by app.py
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    req_q = multiprocessing.Queue()
    res_q = multiprocessing.Queue()
    
    p = multiprocessing.Process(target=start_rate_limiter_process, args=(req_q, res_q))
    p.start()
    
    logger = logging.getLogger(__name__)
    logger.info("Main process: Rate Limiter Process started for testing.")

    # Example usage:
    def dummy_api_call(param1, param2):
        logger.info(f"Dummy API call executed with {param1}, {param2}")
        return f"Result for {param1}-{param2}"

    request_id_1 = "req_1"
    req_q.put((dummy_api_call, ("value1", "value2"), {}, request_id_1))
    
    request_id_2 = "req_2"
    req_q.put((dummy_api_call, ("valueA", "valueB"), {}, request_id_2))

    results = {}
    while len(results) < 2:
        result, req_id = res_q.get()
        if isinstance(result, Exception):
            logger.error(f"Received error for {req_id}: {result}")
        else:
            results[req_id] = result
            logger.info(f"Received result for {req_id}: {result}")
    
    p.terminate()
    p.join()
    logger.info("Main process: Testing complete.")
