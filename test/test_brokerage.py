import asyncio
import asynctest
from mimic.brokerage import *
from mimic.proxy_collection import *


REQUEST_URL_A = 'http://www.google.com/search'


class TestBrokerage(asynctest.ClockedTestCase):
    def setUp(self):
        proxy_a = ProxyProps('http', 'localhost', 8888, 0.1,
                             'us', 'transparent')
        proxy_b = ProxyProps('http', 'localhost', 8889, 0.2)
        proxies = ProxyCollection()
        proxies.register_proxy(proxy_a.to_dict())
        proxies.register_proxy(proxy_b.to_dict())
        self.proxy_collection = proxies

        self.brokerage = Brokerage(proxies)

    async def test_acquire(self):
        proxies = {str(p) for p in self.proxy_collection.proxies}

        res = await self.brokerage.acquire(REQUEST_URL_A, [], 10.0)
        self.assertEqual(res['broker'], "www.google.com")
        self.assertIn(res['proxy'], proxies)
        del res['proxy']

        res = await self.brokerage.acquire(REQUEST_URL_A, [], 10.0)
        self.assertEqual(res['broker'], "www.google.com")
        del res['proxy']
