from __future__ import annotations

import requests
from django.core.cache import cache
from django.utils.functional import cached_property

redis = cache._cache.get_client()
HOST = "http://localhost:9037"


class Benchmark:
    def include(self):
        r1 = requests.get(f"{HOST}/include/")
        assert r1.status_code == 200
        r2 = requests.get(f"{HOST}/include-partial/")
        assert r2.status_code == 200

    def xinclude(self):
        r1 = requests.get(f"{HOST}/xinclude/")
        assert r1.status_code == 200
        r2 = requests.get(f"{HOST}/__xinclude__/?fragment_id={self.fragment_id}")
        assert r2.status_code == 200

    @cached_property
    def fragment_id(self):
        return redis.keys()[0].decode().split(":")[-1]


b = Benchmark()

# %timeit -n 20 b.include()
# >> 152 ms ± 22.3 ms per loop (mean ± std. dev. of 7 runs, 20 loops each)

# %timeit -n 20 b.xinclude()
# >> 354 ms ± 16.7 ms per loop (mean ± std. dev. of 7 runs, 20 loops each)
