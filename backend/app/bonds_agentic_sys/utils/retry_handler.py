"""
Retry Handler Utility
Provides retry logic, timeout handling, and rate limiting for tools and agents
"""

import asyncio
import time
from typing import Callable, Any, Optional, TypeVar, List
from functools import wraps
import logging

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryHandler:
    """
    Handles retries with exponential backoff and timeout
    """

    @staticmethod
    def with_retry(
        func: Callable[..., T],
        max_retries: int = 3,
        backoff_factor: float = 2.0,
        initial_delay: float = 1.0,
        exceptions: tuple = (Exception,),
        timeout: Optional[float] = None,
    ) -> Callable[..., T]:
        """
        Decorator for retry logic with exponential backoff

        Args:
            func: Function to wrap
            max_retries: Maximum number of retry attempts
            backoff_factor: Multiplier for delay between retries
            initial_delay: Initial delay in seconds
            exceptions: Tuple of exceptions to catch and retry on
            timeout: Optional timeout in seconds
        """

        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    if timeout:
                        return await asyncio.wait_for(
                            func(*args, **kwargs), timeout=timeout
                        )
                    else:
                        return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}: {str(e)}. "
                            f"Retrying in {delay:.2f}s..."
                        )
                        await asyncio.sleep(delay)
                        delay *= backoff_factor
                    else:
                        logger.error(
                            f"All {max_retries + 1} attempts failed for {func.__name__}: {str(e)}"
                        )
                except asyncio.TimeoutError:
                    logger.error(f"Timeout after {timeout}s for {func.__name__}")
                    raise
                except Exception as e:
                    # Don't retry on unexpected exceptions
                    logger.error(f"Unexpected error in {func.__name__}: {str(e)}")
                    raise

            if last_exception:
                raise last_exception

        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    if timeout:
                        import signal

                        def timeout_handler(signum, frame):
                            raise TimeoutError(
                                f"Function {func.__name__} timed out after {timeout}s"
                            )

                        signal.signal(signal.SIGALRM, timeout_handler)
                        signal.alarm(int(timeout))

                        try:
                            result = func(*args, **kwargs)
                            signal.alarm(0)
                            return result
                        except TimeoutError:
                            signal.alarm(0)
                            raise
                    else:
                        return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}: {str(e)}. "
                            f"Retrying in {delay:.2f}s..."
                        )
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        logger.error(
                            f"All {max_retries + 1} attempts failed for {func.__name__}: {str(e)}"
                        )
                except Exception as e:
                    logger.error(f"Unexpected error in {func.__name__}: {str(e)}")
                    raise

            if last_exception:
                raise last_exception

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper


class RateLimiter:
    """
    Simple rate limiter using token bucket algorithm
    """

    def __init__(self, max_calls: int, time_window: float = 60.0):
        """
        Initialize rate limiter

        Args:
            max_calls: Maximum number of calls allowed
            time_window: Time window in seconds
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls: List[float] = []
        self.lock = asyncio.Lock()

    async def acquire(self) -> bool:
        """
        Acquire permission to make a call
        Returns True if allowed, False if rate limited
        """
        async with self.lock:
            now = time.time()
            # Remove calls outside the time window
            self.calls = [
                call_time
                for call_time in self.calls
                if now - call_time < self.time_window
            ]

            if len(self.calls) < self.max_calls:
                self.calls.append(now)
                return True
            else:
                return False

    async def wait_if_needed(self):
        """
        Wait if rate limit is reached
        """
        while not await self.acquire():
            # Calculate wait time until oldest call expires
            if self.calls:
                oldest_call = min(self.calls)
                wait_time = self.time_window - (time.time() - oldest_call)
                if wait_time > 0:
                    logger.info(f"Rate limit reached. Waiting {wait_time:.2f}s...")
                    await asyncio.sleep(wait_time)
            else:
                await asyncio.sleep(0.1)


class CircuitBreaker:
    """
    Circuit breaker pattern for failing services
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type = Exception,
    ):
        """
        Initialize circuit breaker

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Time to wait before attempting recovery
            expected_exception: Exception type to count as failures
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "closed"  # closed, open, half_open
        self.lock = asyncio.Lock()

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Call function with circuit breaker protection
        """
        async with self.lock:
            # Check if circuit should be opened
            if self.state == "open":
                if (
                    self.last_failure_time
                    and (time.time() - self.last_failure_time) > self.recovery_timeout
                ):
                    self.state = "half_open"
                    logger.info(
                        "Circuit breaker: Attempting recovery (half-open state)"
                    )
                else:
                    raise Exception("Circuit breaker is OPEN - service unavailable")

            # Try to call the function
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)

                # Success - reset failure count
                if self.state == "half_open":
                    self.state = "closed"
                    logger.info("Circuit breaker: Service recovered (closed state)")
                self.failure_count = 0
                return result

            except self.expected_exception as e:
                self.failure_count += 1
                self.last_failure_time = time.time()

                if self.failure_count >= self.failure_threshold:
                    self.state = "open"
                    logger.error(
                        f"Circuit breaker: OPENED after {self.failure_count} failures. "
                        f"Service will be unavailable for {self.recovery_timeout}s"
                    )

                raise


def create_retry_handler() -> RetryHandler:
    """Factory function"""
    return RetryHandler()
