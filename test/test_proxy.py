import unittest
from itertools import product
from mimic.proxy import Proxy
from mimic.util import *


class TestProxy(unittest.TestCase):
    def test_proxy(self):
        proto, host, port = 'http', 'localhost', 8888
        a = Proxy(proto, host, port, 1.0, 'us', 'high')

        self.assertEqual(str(a), "http://localhost:8888")
        self.assertEqual(str(a), repr(a))

        for args in product([proto, 'https'], [host, 'me'], [port, 8888]):
            if args == (proto, host, port): continue
            b = Proxy(*args, 1.0, 'us', 'high')
            self.assertNotEqual(a, b)

        c = Proxy(proto, host, port, 2.0, 'ca', 'low')
        self.assertEqual(a, c)

