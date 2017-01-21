import json
from aiohttp import web
from mimic.util import parse_and_intern_domain


MIME_JSON = "application/javascript"


def bad_request(err_msg):
    raise web.HTTPBadRequest(text=json.dumps(err_msg), content_type=MIME_JSON)


def csv_param(params, param):
    value = params.get(param, '')
    return value.split(",") if value else []


def required_param(params, param):
    if param not in params:
        bad_request({'err': "{} is a required parameter.".format(param)})
    return params[param]


def human_json(obj):
    return json.dumps(obj, indent=4, sort_keys=True)


class RESTProxyBroker:
    def __init__(self, proxy_collection, brokerage, readme_str=""):
        self._brokerage = brokerage
        self._proxy_collection = proxy_collection
        self._readme_str = readme_str

        self._app = web.Application(debug=True)

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
        return web.Response(text=human_json(self._proxy_collection.proxies),
                            content_type=MIME_JSON)

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

        return web.Response(text=json.dumps({'msg': "OK"}),
                            content_type=MIME_JSON)

    async def acquire_proxy(self, request):
        await request.post()

        url = required_param(request.POST, 'url')

        domain = parse_and_intern_domain(url)
        if not domain:
            bad_request("Could not extract domain from {}".format(domain))

        requirements = csv_param(request.POST, 'requirements')
        max_wait_time = int(request.POST.get('max_wait_time', 60))

        res = await self._brokerage.acquire(url, requirements, max_wait_time)
        return web.Response(text=json.dumps(res), content_type=MIME_JSON)

    async def release_proxy(self, request):
        await request.post()

        broker = required_param(request.POST, 'broker')
        proxy = required_param(request.POST, 'proxy')
        resp_time = float(request.POST.get('response_time', -1))
        failed = request.POST.get('is_failure', 'false').lower() == 'true'

        res = await self._brokerage.release(broker, proxy, resp_time, failed)
        return web.Response(text=json.dumps(res), content_type=MIME_JSON)

    async def list_all_stats(self, request):
        stats = self._brokerage.list_all()
        return web.Response(text=human_json(stats), content_type=MIME_JSON)

    async def get_domain_stats(self, request):
        domain = request.match_info['domain'].lower()
        stats = self._brokerage.list_all().get(domain, {})
        return web.Response(text=human_json(stats), content_type=MIME_JSON)

    async def delete_domain(self, request):
        return web.Response(body=b"not_implemented")


if __name__ == '__main__':
    import argparse
    import os
    import mimic

    # Parse args
    parser = argparse.ArgumentParser(description='A foo that bars')
    parser.add_argument('--host',
                        nargs=1,
                        help='for binding the server',
                        default='localhost')
    parser.add_argument('--port',
                        nargs=1,
                        help='for binding the server',
                        default='8080',
                        type=int)

    command_line_args = vars(parser.parse_args())
    args = {'port': int(command_line_args['port'][0]),
            'host': command_line_args['host'][0]}

    script_dir = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(script_dir, "index.html")) as fp:
        index_html = fp.read()

    proxy_collection = mimic.ProxyCollection()
    brokerage = mimic.Brokerage(proxy_collection)
    server = RESTProxyBroker(proxy_collection, brokerage, index_html)

    server.run(**args)
