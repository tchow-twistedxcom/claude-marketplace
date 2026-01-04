"""
Batch Processor
===============

Handles chunked processing of ASINs with rate limiting and error handling.
"""

import logging
import threading
import time
from typing import Callable, Generator, List, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar('T')


class BatchProcessor:
    """
    Generic batch processor for chunked operations.

    Features:
    - Configurable batch sizes
    - Rate limiting between batches
    - Retry logic for transient failures
    - Progress tracking hooks
    """

    def __init__(
        self,
        batch_size: int = 50,
        delay_between_batches: float = 0.5,
        max_retries: int = 3,
        retry_delay: float = 5.0,
    ):
        """
        Initialize batch processor.

        Args:
            batch_size: Number of items per batch
            delay_between_batches: Seconds to wait between batches
            max_retries: Maximum retry attempts for failed batches
            retry_delay: Seconds to wait before retry
        """
        self.batch_size = batch_size
        self.delay_between_batches = delay_between_batches
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def chunk(self, items: List[T]) -> Generator[List[T], None, None]:
        """Split items into batches."""
        for i in range(0, len(items), self.batch_size):
            yield items[i:i + self.batch_size]

    def process_batches(
        self,
        items: List[T],
        processor: Callable[[List[T]], List],
        on_batch_complete: Optional[Callable[[int, int, List], None]] = None,
        on_batch_error: Optional[Callable[[int, Exception], None]] = None,
    ) -> List:
        """
        Process items in batches.

        Args:
            items: List of items to process
            processor: Function that processes a batch and returns results
            on_batch_complete: Callback(batch_num, total_batches, results)
            on_batch_error: Callback(batch_num, exception)

        Returns:
            Combined results from all batches
        """
        all_results = []
        batches = list(self.chunk(items))
        total_batches = len(batches)

        logger.info(f"Processing {len(items)} items in {total_batches} batches")

        for batch_num, batch in enumerate(batches, 1):
            batch_results = self._process_batch_with_retry(
                batch=batch,
                processor=processor,
                batch_num=batch_num,
                on_error=on_batch_error,
            )

            all_results.extend(batch_results)

            if on_batch_complete:
                on_batch_complete(batch_num, total_batches, batch_results)

            # Rate limiting delay (except for last batch)
            if batch_num < total_batches:
                time.sleep(self.delay_between_batches)

        return all_results

    def _process_batch_with_retry(
        self,
        batch: List[T],
        processor: Callable[[List[T]], List],
        batch_num: int,
        on_error: Optional[Callable[[int, Exception], None]] = None,
    ) -> List:
        """Process a single batch with retry logic."""
        last_error = None

        for attempt in range(1, self.max_retries + 1):
            try:
                return processor(batch)
            except Exception as e:
                last_error = e
                logger.warning(
                    f"Batch {batch_num} attempt {attempt}/{self.max_retries} failed: {e}"
                )

                if on_error:
                    on_error(batch_num, e)

                if attempt < self.max_retries:
                    # Exponential backoff
                    wait_time = self.retry_delay * (2 ** (attempt - 1))
                    logger.info(f"Retrying in {wait_time:.1f}s...")
                    time.sleep(wait_time)

        # All retries exhausted
        logger.error(f"Batch {batch_num} failed after {self.max_retries} attempts")
        raise last_error

    def process_items_individually(
        self,
        items: List[T],
        processor: Callable[[T], Optional[T]],
        on_success: Optional[Callable[[T], None]] = None,
        on_error: Optional[Callable[[T, Exception], None]] = None,
        rate_limit: float = 0.0,
    ) -> tuple:
        """
        Process items one at a time with individual error handling.

        Args:
            items: List of items to process
            processor: Function that processes a single item
            on_success: Callback for successful processing
            on_error: Callback for failed processing
            rate_limit: Seconds to wait between items

        Returns:
            Tuple of (successful_results, failed_items)
        """
        successful = []
        failed = []

        for item in items:
            try:
                result = processor(item)
                if result is not None:
                    successful.append(result)
                if on_success:
                    on_success(item)
            except Exception as e:
                failed.append((item, str(e)))
                if on_error:
                    on_error(item, e)

            if rate_limit > 0:
                time.sleep(rate_limit)

        return successful, failed


class RateLimiter:
    """
    Thread-safe token bucket rate limiter for API calls.
    """

    def __init__(self, rate: float, burst: int = 1):
        """
        Initialize rate limiter.

        Args:
            rate: Requests per second
            burst: Maximum burst size
        """
        self.rate = rate
        self.burst = burst
        self._tokens = burst
        self._last_time = time.time()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        """Wait until a request can be made (thread-safe)."""
        while True:
            with self._lock:
                now = time.time()
                elapsed = now - self._last_time
                self._last_time = now

                # Add tokens based on elapsed time
                self._tokens = min(self.burst, self._tokens + elapsed * self.rate)

                if self._tokens >= 1:
                    self._tokens -= 1
                    return

                # Calculate wait time while holding lock
                wait_time = (1 - self._tokens) / self.rate

            # Sleep outside the lock to allow other threads to proceed
            time.sleep(wait_time)
