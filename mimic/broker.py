import asyncio
import logging


LOGGER = logging.getLogger('mimic.broker')
LOGGER.setLevel(logging.INFO)
LOGGER.addHandler(logging.StreamHandler())


THIRTY_SECONDS = 30
ONE_MINUTE = 60
ONE_HOUR = ONE_MINUTE * 60


class Broker:
    """
    A broker manages granting proxy resources to a client.
    """

    def __init__(self, domain_monitor, loop=None,
                 return_delay=THIRTY_SECONDS,
                 auto_return_delay=ONE_MINUTE,
                 bad_return_delay=ONE_HOUR,
                 max_consecutive_failures=3):

        self._loop = loop or asyncio.get_event_loop()
        self._monitor = domain_monitor
        self._return_delay = return_delay
        self._auto_return_delay = auto_return_delay
        self._bad_return_delay = bad_return_delay
        self._max_consecutive_failures = max_consecutive_failures

        self._consecutive_failures = {}
        self._tasks = {}  # proxy -> (status, task)

        LOGGER.info("Initiated Broker on %s", self._monitor.domain)

    async def acquire(self, *requirements, max_wait_time=ONE_MINUTE):
        proxy = self._monitor.acquire(*requirements)

        # If the proxy is None, there were no proxies currently available.
        # Sleep for the maximum_wait_time, then try again.
        # This doesn't queue at all. It's just stochastic.
        if proxy is None:  # None currently available.
            LOGGER.info("Waiting %s seconds to acquire on %s",
                        max_wait_time, self._monitor.domain)
            await asyncio.sleep(max_wait_time)
            proxy = self._monitor.acquire(*requirements)

        # No proxy acquired within the max_wait_time.
        if proxy is None:
            LOGGER.info("Failed to acquire on %s", self._monitor.domain)
            return None  # None could be acquired.

        # Create auto-return task.
        coro = self._return_after(proxy, -1, self._auto_return_delay)
        self._tasks[proxy] = self._loop.create_task(coro)

        LOGGER.info("Acquire %s on %s", proxy, self._monitor.domain)
        return proxy

    def release(self, proxy, response_time, is_failure=False):
        self._cancel_tasks_on(proxy)

        # TODO: Add check for None

        if is_failure:
            failures = self._consecutive_failures.get(proxy, 0) + 1
            if failures > self._max_consecutive_failures:
                LOGGER.info("Proxy %s failed out on %s",
                            proxy, self._monitor.domain)
            else:
                self._consecutive_failures[proxy] = failures
                coro = self._return_after(proxy, -1, self._bad_return_delay)
                self._tasks[proxy] = self._loop.create_task(coro)

        else:
            coro = self._return_after(proxy, response_time, self._return_delay)
            self._tasks[proxy] = self._loop.create_task(coro)

    async def _return_after(self, proxy, response_time, wait_seconds):
        print("Returning {} in {} seconds".format(proxy, wait_seconds))
        LOGGER.info("Waiting %s to release %s on %s",
                    wait_seconds, proxy, self._monitor.domain)
        try:
            await asyncio.sleep(wait_seconds)
            self._monitor.release(proxy, response_time)
        except asyncio.CancelledError:
            pass

    def _cancel_tasks_on(self, proxy):
        existing_task = self._tasks.get(proxy)
        if existing_task:
            existing_task.cancel()

    def register(self, proxy):
        self._monitor.register(proxy)

    def delist(self, proxy):
        self._monitor.delist(proxy)
        self._cancel_tasks_on(proxy)

    def stats(self):
        return self._monitor.stats()

    @property
    def monitor(self):
        return self._monitor
