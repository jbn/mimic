#!/usr/bin/env python

import argparse
import asyncio
import requests

from mimic.util import proxy_dicts_from_proxy_broker_proxy, url_from_proxy
from proxybroker import Broker


async def register(proxies, endpoint):
    while True:
        proxy = await proxies.get()
        if proxy is None:
            break
        for p in proxy_dicts_from_proxy_broker_proxy(proxy):
            url = url_from_proxy(p)
            resp = requests.post(endpoint, data=p).content
            print("Resp on {}: {} on ".format(url, resp))


if __name__ == '__main__':
    desc = 'Collect and inject proxies from public sources'
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('filepath',
                        metavar='FILEPATH',
                        help='a file with proxies to process')
    parser.add_argument('endpoint',
                        metavar='ENDPOINT',
                        help='url to mimic server (with no trailing slash)')
    args = parser.parse_args()
    endpoint = args.endpoint + '/proxies/register'
    file_path = args.filepath

    with open(file_path) as fp:
        data = fp.read()

    proxies = asyncio.Queue()
    broker = Broker(proxies)

    find_coro = broker.find(types=[('HTTP', ('Anonymous', 'High'))],
                            strict=True,
                            data=data)
    register_coro = register(proxies, endpoint)

    tasks = asyncio.gather(find_coro, register_coro)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(tasks)
