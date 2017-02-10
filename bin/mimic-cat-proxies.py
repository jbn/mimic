#!/usr/bin/env python

import argparse
import requests


if __name__ == '__main__':
    desc = 'Collect and inject proxies from public sources'
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('--endpoint',
                        action='store',
                        dest='endpoint',
                        help='url to mimic server (with no trailing slash)',
                        default='http://localhost:8901')
    endpoint = parser.parse_args().endpoint + '/proxies'

    for proxy in requests.get(endpoint).json():
        print(proxy)
