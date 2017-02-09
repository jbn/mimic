import sys
import unittest
from contextlib import contextmanager
from shlex import split as shell_split

from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop
from mimic.util import ProxyProps
from mimic.server import *


@contextmanager
def swap_argv(replacement):
    original = sys.argv
    sys.argv = shell_split(replacement)

    try:
        yield
    finally:
        sys.argv = original


class TestServerUtil(unittest.TestCase):
    def test_required_param(self):
        self.assertEqual(required_param({'bird': 'brain'}, 'bird'), 'brain')

        with self.assertRaises(web.HTTPBadRequest):
            required_param({}, 'bird')

    def test_csv_param(self):
        self.assertEqual(csv_param({'q': "a,b,c"}, 'q'), list('abc'))

    def test_human_json(self):
        self.assertEqual(human_json({'a': 10, 'b': 20}),
                         '{\n    "a": 10,\n    "b": 20\n}')

        self.assertEqual(human_json({}), '{}')

    def test_parse_args_defaults(self):
        with swap_argv('run_server.py'):
            args = parse_args()
            self.assertEqual(args.host, 'localhost')
            self.assertEqual(args.port, 8080)
            self.assertFalse(args.debug)

    def test_parse_args(self):
        with swap_argv('run_server.py --debug --host gibson --port 80'):
            args = parse_args()
            self.assertEqual(args.host, 'gibson')
            self.assertEqual(args.port, 80)
            self.assertTrue(args.debug)


class TestRestProxyBroker(AioHTTPTestCase):

    def get_app(self, loop):
        proxies = ProxyCollection()
        a = ProxyProps('http', 'proxy-a', 8888, 0.1)
        b = ProxyProps('http', 'proxy-b', 8888, 0.1)
        proxies.register_proxy(a.to_dict())
        proxies.register_proxy(b.to_dict())
        brokerage = Brokerage(proxies, broker_opts={'loop': loop})
        app = RESTProxyBroker(proxy_collection=proxies,
                              brokerage=brokerage,
                              loop=loop)._app
        return app

    @unittest_run_loop
    async def test_get_index(self):
        req = await self.client.request('GET', "/")
        self.assertEqual(req.status, 200)
        self.assertEqual(await req.text(), DEFAULT_README)

    @unittest_run_loop
    async def test_list_proxies(self):
        req = await self.client.request('GET', '/proxies')
        self.assertEqual(req.status, 200)
        self.assertEqual(sorted(await req.json()),
                         ["HTTP://PROXY-A:8888", "HTTP://PROXY-B:8888"])

    @unittest_run_loop
    async def test_register_proxy_good_req(self):
        req = await self.client.request('POST',
                                        "/proxies/register",
                                        data={'proto': 'https',
                                              'host': 'localhost',
                                              'port': '9999',
                                              'resp_time': 0.1})
        self.assertEqual(req.status, 200)
        self.assertEqual(await req.json(), {'msg': "OK"})

        req = await self.client.request('GET', '/proxies')
        self.assertEqual(req.status, 200)
        self.assertIn("HTTPS://LOCALHOST:9999", await req.json())

    @unittest_run_loop
    async def test_acquire_good(self):
        req = await self.client.request('POST', '/proxies/acquire',
                                        data={'url': "http://google.com/",
                                              'max_wait_time': 60})
        self.assertEqual(req.status, 200)
        resp = await req.json()
        self.assertEqual(resp['broker'], 'google.com')
        self.assertIn(resp['proxy'], {'HTTP://PROXY-A:8888',
                                      'HTTP://PROXY-B:8888'})

    @unittest_run_loop
    async def test_acquire_bad(self):
        req = await self.client.request('POST', '/proxies/acquire')
        self.assertEqual(req.status, 400)

    @unittest_run_loop
    async def test_release_proxy(self):
        req = await self.client.request('POST', '/proxies/acquire',
                                        data={'url': "http://google.com/",
                                              'max_wait_time': 60})
        proxy = await req.json()

        req = await self.client.request('POST', '/proxies/release',
                                        data=proxy)
        self.assertEqual(req.status, 200)
        self.assertEqual(await req.json(), True)

    @unittest_run_loop
    async def test_list_all_stats(self):
        req = await self.client.request('GET', '/domains')
        self.assertEqual(req.status, 200)
        self.assertEqual(await req.json(), {})

        req = await self.client.request('POST', '/proxies/acquire',
                                        data={'url': "http://google.com/",
                                              'max_wait_time': 60})

        self.assertEqual(req.status, 200)

        req = await self.client.request('GET', '/domains')
        self.assertEqual(req.status, 200)
        self.assertEqual(await req.json(),
                         {'google.com': {'acquisitions_processed': 1,
                                         'available': 1,
                                         'avg_resp_time': 0.1,
                                         'indices': {}}})

    @unittest_run_loop
    async def test_get_domain_stats(self):
        req = await self.client.request('GET', '/domains/google.com')
        self.assertEqual(req.status, 200)
        self.assertEqual(await req.json(), {})

        req = await self.client.request('POST', '/proxies/acquire',
                                        data={'url': "http://google.com/",
                                              'max_wait_time': 60})

        self.assertEqual(req.status, 200)

        req = await self.client.request('GET', '/domains/google.com')
        self.assertEqual(req.status, 200)
        self.assertEqual(await req.json(),
                         {'acquisitions_processed': 1,
                          'available': 1,
                          'avg_resp_time': 0.1,
                          'indices': {}})