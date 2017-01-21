class Proxy:
    __slots__ = ['proto', 'host', 'port', 'resp_time', 'geo', 'anon_level']

    def __init__(self, proto, host, port, resp_time, geo, anon_level):
        self.proto = proto
        self.host = host
        self.port = port
        self.resp_time = resp_time
        self.geo = geo
        self.anon_level = anon_level

    def __str__(self):
        return "{}://{}:{}".format(self.proto, self.host, self.port)

    def __repr__(self):
        return self.__str__()

    def _key(self):
        return self.proto, self.host, self.port

    def __eq__(self, other):
        return self._key() == other._key()

    def __hash__(self):
        return hash(self._key())