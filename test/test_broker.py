import asyncio
import asynctest
from mimic.broker import *
from mimic.util import ProxyProps
from mimic.domain_monitor import DomainMonitor


REQUEST_URL_A = 'http://google.com/search'


class TestBrokerage(asynctest.ClockedTestCase):
    def setUp(self):
        self.domain_monitor = DomainMonitor('google.com')

        proxy_a = ProxyProps('http', 'proxy-a', 8888, 0.1)
        proxy_b = ProxyProps('http', 'proxy-b', 8888, 0.1)
        self.domain_monitor.register(proxy_a)
        self.domain_monitor.register(proxy_b)

        self.proxy_strs = {str(proxy_a), str(proxy_b)}

    async def test_acquire_release_easy(self):
        # Create a broker.
        broker = Broker(self.domain_monitor)

        # There should be no tasks yet and two proxies available.
        self.assertEqual(len(broker._tasks), 0)
        self.assertEqual(broker.stats()['available'], 2)

        # Acquire one proxy. There are two proxies available (via ``setUp``),
        # so this should return instantly.
        proxy = await broker.acquire()
        self.assertIn(proxy, self.proxy_strs)

        # Now, there should only be one proxy available.
        self.assertEqual(broker.stats()['available'], 1)

        # The acquisition creates a ``_return_after`` coroutine, which
        # automatically returns the proxy if the client failed to do so.
        orig_tasks = list(broker._tasks.values())
        self.assertEqual(len(orig_tasks), 1)

        # Return the proxy prior to the automatic return timeout.
        # Simulate a quick, successful response.
        broker.release(proxy, 0.2, False)

        # There should *still* only be one proxy available.
        # But, the enqueued tasks should be swapped.
        self.assertEqual(broker.stats()['available'], 1)
        cur_tasks = list(broker._tasks.values())
        self.assertEqual(len(cur_tasks), 1)
        self.assertNotEqual(id(cur_tasks[0]), id(orig_tasks[0]))

        # Let's fast forward through time to when the task should auto-return.
        await self.advance(THIRTY_SECONDS+1)

        # There should now be no active tasks and there should be two
        # proxies available.
        self.assertEqual(len(broker._tasks), 0)
        self.assertEqual(broker.stats()['available'], 2)
        self.assertEqual(broker.stats()['avg_resp_time'],
                         (0.1 + 0.2) / 2)

    async def test_acquired_but_never_released(self):
        # Create a broker.
        broker = Broker(self.domain_monitor)

        # There should be no tasks yet and two proxies available.
        self.assertEqual(len(broker._tasks), 0)
        self.assertEqual(broker.stats()['available'], 2)

        # Acquire one proxy. There are two proxies available (via ``setUp``),
        # so this should return instantly.
        proxy = await broker.acquire()
        self.assertIn(proxy, self.proxy_strs)

        # Now, there should only be one proxy available.
        self.assertEqual(broker.stats()['available'], 1)

        # The acquisition creates a ``_return_after`` coroutine, which
        # automatically returns the proxy if the client failed to do so.
        orig_tasks = list(broker._tasks.values())
        self.assertEqual(len(orig_tasks), 1)

        # Let's fast forward through time, but prior to auto-return.
        await self.advance(THIRTY_SECONDS+1)

        # There should *still* only be one proxy available.
        self.assertEqual(broker.stats()['available'], 1)

        # Fast forward again, past the auto return time.
        await self.advance(THIRTY_SECONDS + 1)

        # There should now be no active tasks and there should be two
        # proxies available.
        self.assertEqual(len(broker._tasks), 0)
        self.assertEqual(broker.stats()['available'], 2)
        self.assertEqual(broker.stats()['avg_resp_time'],
                         (0.1 + THIRTY_SECONDS) / 2)

    async def test_acquired_and_released_failed_request(self):
        # Create a broker.
        broker = Broker(self.domain_monitor)

        # There should be no tasks yet and two proxies available.
        self.assertEqual(len(broker._tasks), 0)
        self.assertEqual(broker.stats()['available'], 2)

        # Acquire one proxy. There are two proxies available (via ``setUp``),
        # so this should return instantly.
        proxy = await broker.acquire()
        self.assertIn(proxy, self.proxy_strs)

        # Now, there should only be one proxy available.
        self.assertEqual(broker.stats()['available'], 1)

        # The acquisition creates a ``_return_after`` coroutine, which
        # automatically returns the proxy if the client failed to do so.
        orig_tasks = list(broker._tasks.values())
        self.assertEqual(len(orig_tasks), 1)

        # Return the proxy prior to the automatic return timeout.
        # Simulate a quick, successful response.
        broker.release(proxy, 0.2, True)

        # There should *still* only be one proxy available.
        # But, the enqueued tasks should be swapped.
        self.assertEqual(broker.stats()['available'], 1)
        cur_tasks = list(broker._tasks.values())
        self.assertEqual(len(cur_tasks), 1)
        self.assertNotEqual(id(cur_tasks[0]), id(orig_tasks[0]))

        # Let's fast forward through time to the normal task auto release time.
        await self.advance(THIRTY_SECONDS + 1)

        # There should still be a task, with no additional proxy available.
        # Failures return much later.
        self.assertEqual(len(broker._tasks), 1)
        self.assertEqual(broker.stats()['available'], 1)

        # Now, lets fast forward another 10 minutes
        await self.advance(10 * ONE_MINUTE)

        # There should now be no active tasks and there should be two
        # proxies available.
        self.assertEqual(len(broker._tasks), 0)
        self.assertEqual(broker.stats()['available'], 2)

        # But it is time penalized for selection because it failed.
        self.assertEqual(broker.stats()['avg_resp_time'],
                         (0.1 + THIRTY_SECONDS) / 2)

    async def test_good_release_resets_failure_counter(self):
        # Create a broker.
        broker = Broker(self.domain_monitor)
        proxy = await broker.acquire()
        broker._consecutive_failures[proxy] = 1
        self.assertEqual(broker._consecutive_failures[proxy], 1)

        broker.release(proxy, 10, False)
        self.assertNotIn(proxy, broker._consecutive_failures)

    async def test_bad_release_removes_if_max_failures(self):
        # Create a broker.
        broker = Broker(self.domain_monitor)
        self.assertEqual(broker.stats()['available'], 2)

        proxy = await broker.acquire()
        broker._consecutive_failures[proxy] = 2

        broker.release(proxy, 0.1, True)
        self.assertNotIn(proxy, broker._consecutive_failures)
        self.assertEqual(broker.stats()['available'], 1)

    async def test_register_deregister(self):
        broker = Broker(self.domain_monitor)
        proxy = ProxyProps('http', 'proxy-c', 8888, 0.1)

        broker.register(proxy)
        self.assertEqual(broker.stats()['available'], 3)

        broker.delist(str(proxy))
        self.assertEqual(broker.stats()['available'], 2)

    async def test_wont_reregister(self):
        broker = Broker(self.domain_monitor)
        proxy_dup = ProxyProps('http', 'proxy-a', 8888, 0.1)

        broker.register(proxy_dup)
        self.assertEqual(broker.stats()['available'], 2)

    async def test_acquire_waiting(self):
        broker = Broker(self.domain_monitor)
        proxy_dup = ProxyProps('http', 'proxy-a', 8888, 0.1)

        # Consume both proxies.
        proxy_a = await broker.acquire()
        proxy_b = await broker.acquire()
        self.assertEqual(broker.stats()['available'], 0)

        # Create a task that will wait for availability.
        acquired = []
        async def acquire_post_clock():
            acquired.append(await broker.acquire())
        post_clock = self.loop.create_task(acquire_post_clock())

        # Fast forward thirty seconds, it should still be waiting.
        await self.advance(THIRTY_SECONDS)
        self.assertFalse(post_clock.done())
        self.assertEqual(broker.stats()['available'], 0)

        # Now, forward past the max wait time.
        # Two proxies were returned. One was acquired.
        await self.advance(THIRTY_SECONDS+1)
        self.assertTrue(post_clock.done())
        self.assertEqual(broker.stats()['available'], 1)
        self.assertIn(acquired[0], self.proxy_strs)

    async def test_acquire_waiting_fails(self):
        broker = Broker(self.domain_monitor)

        # Consume both proxies.
        proxy_a = await broker.acquire()
        proxy_b = await broker.acquire()
        self.assertEqual(broker.stats()['available'], 0)

        # Try to acquire too quickly (prior to any return availability).
        acquired = []
        async def acquire_post_clock():
            acquired.append(await broker.acquire(max_wait_time=0.01))
        post_clock = self.loop.create_task(acquire_post_clock())
        await self.advance(10)
        self.assertTrue(post_clock.done())

        # Acquire should return None, as a sentinel.
        self.assertEqual([None], acquired)





