import unittest
from mimic.util import *


class TestGetAccessor(unittest.TestCase):
    def test_parse_and_intern_domain(self):
        domain = "www.yahoo.com"
        url_a = "http://www.yahoo.com/api/pages?id=1"
        url_b = "http://www.yahoo.com/api/pages?id=2"

        a, b = parse_and_intern_domain(url_a), parse_and_intern_domain(url_b)
        self.assertEqual(a, b)
        self.assertEqual(a, domain)
        self.assertIs(a, b)
        self.assertIsNot(a, domain)
