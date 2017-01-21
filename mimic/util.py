from six.moves.urllib.parse import urlparse


PROXY_DEFAULTS = {'proto': None,
                  'host': None,
                  'port': None,
                  'resp_time': 0,
                  'geo': "UNK",
                  'anon_level': "HTTP-TRANSPARENT"}


INTERNED_DOMAINS = {}


def parse_and_intern_domain(url):
    """
    Parse the url; extract the name; and, return the interned (cached) name.

    This allows for fast `is` comparison. And, it compacts memory.

    :param url: the url to some resource
    :return: the interned domain
    """
    domain = urlparse(url).netloc.lower()

    # This form of interning compacts memory.
    # Also it allows for `is` comparison.
    interned_domain = INTERNED_DOMAINS.get(domain)
    if interned_domain is None:
        INTERNED_DOMAINS[domain] = domain
        return domain
    else:
        return interned_domain


def proxy_dicts_from_proxy_broker_proxy(proxy):
    ds = []
    for scheme in proxy.schemes:
        for proto, anon_level in proxy.types.items():
            if anon_level is None:
                anon_level = ""
            else:
                anon_level = "-" + anon_level.upper()

            d = PROXY_DEFAULTS.copy()

            d['proto'], d['host'], d['port'] = scheme, proxy.host, proxy.port
            d['resp_time'] = proxy.avg_resp_time
            d['geo'] = proxy.geo.code
            d['anon_level'] = proto + anon_level

            ds.append(d)
    return ds


def url_from_proxy(proxy_dict):
    return "{proto}://{host}:{port}".format(**proxy_dict)


