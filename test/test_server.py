import unittest
from aiohttp import web
from mimic.server import *


class TestDomainMonitor(unittest.TestCase):
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