import json
from aiohttp import web
from asyncio import get_event_loop
from mimic.util import parse_and_intern_domain
from mimic import ProxyCollection, Brokerage


def bad_request(err_msg):
    raise web.HTTPBadRequest(text=json.dumps(err_msg),
                             content_type="application/javascript")


def csv_param(params, param):
    value = params.get(param, '')
    return value.split(",") if value else []


def required_param(params, param):
    if param not in params:
        bad_request({'err': "{} is a required parameter.".format(param)})
    return params[param]


def human_json(obj):
    return json.dumps(obj, indent=4, sort_keys=True)


def load_default_readme():
    import os
    script_dir = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(script_dir, "index.html")) as fp:
        return fp.read()

DEFAULT_README = load_default_readme()


class RESTProxyBroker:
    def __init__(self, proxy_collection=None,
                 brokerage=None,
                 readme_str=DEFAULT_README,
                 debug=True,
                 loop=None):

        self._proxy_collection = proxy_collection or ProxyCollection()
        self._brokerage = brokerage or Brokerage(self._proxy_collection)
        self._readme_str = readme_str

        self._app = web.Application(loop=loop or get_event_loop(), debug=debug)

        routes = [('GET',    "/",                 self.readme),
                  ('GET',    "/proxies",          self.list_proxies),
                  ('POST',   "/proxies/register", self.register_proxy),
                  ('POST',   "/proxies/acquire",  self.acquire_proxy),
                  ('POST',   "/proxies/release",  self.release_proxy),
                  ('GET',    "/domains",          self.list_all_stats),
                  ('GET',    "/domains/{domain}", self.get_domain_stats),
                  ('DELETE', "/domains/{domain}", self.delete_domain)]

        for route_triplet in routes:
            self._app.router.add_route(*route_triplet)

    def run(self, *args, **kwargs):
        web.run_app(self._app, *args, **kwargs)

    async def readme(self, request):
        return web.Response(text=self._readme_str, content_type='text/html')

    async def list_proxies(self, request):
        proxy_strs = [str(proxy) for proxy in self._proxy_collection.proxies]
        return web.json_response(proxy_strs, dumps=human_json)

    async def register_proxy(self, request):
        await request.post()

        proxy = {k: required_param(request.POST, k).upper()
                 for k in ['proto', 'host', 'port']}
        proxy['port'] = int(proxy['port'])
        for k in 'resp_time', 'geo', 'anon_level':
            if k in request.POST:
                proxy[k] = request.POST[k].upper()
        if 'resp_time' in proxy:
            proxy['resp_time'] = float(proxy['resp_time'])

        self._proxy_collection.register_proxy(proxy)

        return web.json_response({'msg': "OK"})

    async def acquire_proxy(self, request):
        await request.post()

        url = required_param(request.POST, 'url')

        domain = parse_and_intern_domain(url)
        if not domain:
            bad_request("Could not extract domain from {}".format(domain))

        requirements = csv_param(request.POST, 'requirements')
        max_wait_time = int(request.POST.get('max_wait_time', 60))

        res = await self._brokerage.acquire(url, requirements, max_wait_time)
        return web.json_response(res)

    async def release_proxy(self, request):
        await request.post()

        broker = required_param(request.POST, 'broker')
        proxy = required_param(request.POST, 'proxy')
        if proxy is None:
            return web.Response(text='No such proxy', status=403)
        resp_time = float(request.POST.get('response_time', 60.0))
        failed = request.POST.get('is_failure', 'false').lower() == 'true'

        res = await self._brokerage.release(broker, proxy, resp_time, failed)
        return web.json_response(res)

    async def list_all_stats(self, request):
        stats = self._brokerage.list_all()
        return web.json_response(stats, dumps=human_json)

    async def get_domain_stats(self, request):
        domain = request.match_info['domain'].lower()
        stats = self._brokerage.list_all().get(domain, {})
        return web.json_response(stats, dumps=human_json)

    async def delete_domain(self, request):
        # TODO
        return web.Response(body=b"not_implemented")


def parse_args():
    import argparse

    parser = argparse.ArgumentParser(description='Serve you some proxies')

    parser.add_argument('--host',
                        action='store',
                        dest='host',
                        help='for binding the server',
                        default='localhost')

    parser.add_argument('--port',
                        action='store',
                        dest='port',
                        help='for binding the server',
                        default='8080',
                        type=int)

    parser.add_argument('--debug', dest='debug', action='store_true')

    return parser.parse_args()


if __name__ == '__main__':
    command_line_args = parse_args()

    server = RESTProxyBroker(debug=command_line_args.debug)
    server.run(host=command_line_args.host, port=int(command_line_args.port))
