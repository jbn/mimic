import asyncio
import logging


LOGGER = logging.getLogger('mimic.broker')
LOGGER.setLevel(logging.INFO)
LOGGER.addHandler(logging.StreamHandler())


ONE_SECOND = 1
THIRTY_SECONDS = 30
ONE_MINUTE = 60


class Broker:
    """
    Manages proxies for clients.

    The broker will automatically release a proxy if the client did not
    release it in the agreed upon polite time period (``auto_return_delay`).
    If the client did release it, the broker waits a bit (``return_delay``)
    before truly releasing it, effectively throttling connections through that
    proxy. If the client marked the request as a failure (e.g. a ReCAPTCHA
    message situation), the proxy is available only after a longer delay
    (``bad_return_delay``), assuming the maximum number of consecutive
    failures for that proxy has not been exceeded. If it has been exceeded,
    that proxy is removed permanently.
    """
    def __init__(self, domain_monitor, loop=None,
                 return_delay=THIRTY_SECONDS,
                 auto_return_delay=ONE_MINUTE,
                 bad_return_delay=10*ONE_MINUTE,
                 max_consecutive_failures=3,
                 failed_release_resp_time=THIRTY_SECONDS,
                 retry_time=ONE_SECOND):

        self._loop = loop or asyncio.get_event_loop()
        self._monitor = domain_monitor
        self._return_delay = return_delay
        self._auto_return_delay = auto_return_delay
        self._bad_return_delay = bad_return_delay
        self._max_consecutive_failures = max_consecutive_failures
        self._failed_release_resp_time = failed_release_resp_time
        self._retry_time = retry_time

        self._consecutive_failures = {}
        self._tasks = {}  # proxy -> (status, task)

        LOGGER.info("Initiated Broker on %s", self._monitor.domain)

    async def acquire(self, *requirements, max_wait_time=ONE_MINUTE):
        """
        Acquire a proxy for use with this broker's domain.

        :param requirements: the tagged requirements for a proxy
        :param max_wait_time: the maximum time to wait before failing
        :return: the proxy string, or None if the ``max_wait_time`` was
            exceeded.
        """
        start_time = self._loop.time()
        proxy = self._monitor.acquire(*requirements)

        # If the proxy is None, there were no proxies currently available.
        # Sleep for the maximum_wait_time, then try again.
        # This doesn't FIFO queue at all. It's just stochastic.
        while proxy is None and self._loop.time() - start_time < max_wait_time:
            await asyncio.sleep(self._retry_time)
            proxy = self._monitor.acquire(*requirements)

        # No proxy acquired within the max_wait_time.
        if proxy is None:
            LOGGER.info("Failed to acquire on %s", self._monitor.domain)
            LOGGER.info("\tcount={}".format(len(self._monitor._proxies)))
            return None  # None could be acquired.

        # Create auto-return task.
        coro = self._return_after(proxy,
                                  self._failed_release_resp_time,
                                  self._auto_return_delay)
        self._tasks[proxy] = self._loop.create_task(coro)

        LOGGER.info("Acquire %s on %s", proxy, self._monitor.domain)
        LOGGER.info("\tcount={}".format(len(self._monitor._proxies)))
        return proxy

    def release(self, proxy, response_time, is_failure=False):
        """
        Release the proxy so others can acquire it.

        :param proxy: the proxy string
        :param response_time: the time it took to make a request using the
            given proxy
        :param is_failure: if True, indicate the proxy failed to yield the
            targeted page
        """
        self._cancel_tasks_on(proxy)

        # TODO: Remove these checks!
        assert proxy is not None, "Released a NONE!"

        if is_failure:
            failures = self._consecutive_failures.get(proxy, 0) + 1
            if failures >= self._max_consecutive_failures:
                LOGGER.info("Proxy %s failed out on %s",
                            proxy, self._monitor.domain)
                del self._consecutive_failures[proxy]
            else:
                self._consecutive_failures[proxy] = failures
                coro = self._return_after(proxy,
                                          self._failed_release_resp_time,
                                          self._bad_return_delay)
                self._tasks[proxy] = self._loop.create_task(coro)

        else:
            # This request was successful. Reset consecutive failures counter.
            if proxy in self._consecutive_failures:
                del self._consecutive_failures[proxy]

            coro = self._return_after(proxy, response_time, self._return_delay)
            self._tasks[proxy] = self._loop.create_task(coro)

    async def _return_after(self, proxy, response_time, wait_seconds):
        """
        Release a proxy for subsequent usage after some throttling delay.

        :param proxy: the proxy string
        :param response_time: the time a request took using this proxy
        :param wait_seconds: the number of seconds to wait before returning
            the proxy
        """
        # TODO: Add check for None
        assert proxy is not None, "Released a NONE!"

        LOGGER.info("Waiting %s to release %s on %s",
                    wait_seconds, proxy, self._monitor.domain)
        try:
            # This is a cheap form of per-domain, per-proxy throttling.
            await asyncio.sleep(wait_seconds)
            self._monitor.release(proxy, response_time)

            # Only one task should exist at any moment each any proxy.
            if proxy in self._tasks:
                del self._tasks[proxy]
        except asyncio.CancelledError:
            pass

    def _cancel_tasks_on(self, proxy):
        existing_task = self._tasks.get(proxy)
        if existing_task:
            existing_task.cancel()

    def register(self, proxy):
        """
        Register a proxy for use with this broker.
        """
        self._monitor.register(proxy)

    def delist(self, proxy):
        """
        Remove a proxy from this broker's pool.
        """
        self._monitor.delist(proxy)
        self._cancel_tasks_on(proxy)

    def stats(self):
        """
        :return: the underlying monitor's stats
        """
        return self._monitor.stats()

    @property
    def monitor(self):
        return self._monitor
