import logging
from urllib.parse import urlparse


PROXY_DEFAULTS = {'proto': None,
                  'host': None,
                  'port': None,
                  'resp_time': 0,
                  'geo': "UNK",
                  'anon_level': "HTTP-TRANSPARENT"}


INTERNED_DOMAINS = {}


def setup_logger(service, default_level=logging.INFO):
    """
    Setup a logger for a given service with a StreamHandler attached.

    :param service: the service to log (i.e. `mimic.<service>`)
    :param default_level: the logging level
    :return: the logger
    """
    logger = logging.getLogger('mimic.' + service)
    logger.setLevel(default_level)
    logger.addHandler(logging.StreamHandler())

    return logger


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


def url_from_proxy(proxy_dict):
    return "{proto}://{host}:{port}".format(**proxy_dict)


class ProxyProps:
    """
    A thin class to declare a proxy's properties.
    """
    __slots__ = ['proto', 'host', 'port', 'resp_time', 'geo', 'anon_level']

    def __init__(self, proto, host, port, resp_time,
                 geo=None, anon_level=None):
        self.proto = proto
        self.host = host
        self.port = port
        self.resp_time = resp_time
        self.geo = geo
        self.anon_level = anon_level

    def __str__(self):
        return "{}://{}:{}".format(self.proto, self.host, self.port).upper()

    def __repr__(self):
        return self.__str__()

    def to_dict(self):
        return {'proto': self.proto,
                'host': self.host,
                'port': self.port,
                'resp_time': self.resp_time,
                'geo': self.geo,
                'anon_level': self.anon_level}

    def _key(self):
        return self.proto, self.host, self.port

    def __eq__(self, other):
        return self._key() == other._key()

    def __hash__(self):
        return hash(self._key())


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

