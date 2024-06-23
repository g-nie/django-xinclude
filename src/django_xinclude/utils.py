from __future__ import annotations

from contextlib import contextmanager


@contextmanager
def profile_and_print(filename="profile.stats"):  # type: ignore[no-untyped-def]
    import cProfile
    import pstats

    profiler = cProfile.Profile()
    profiler.enable()

    try:
        yield
    finally:
        profiler.disable()
    # pstats.Stats(profiler).sort_stats(pstats.SortKey.CUMULATIVE).print_stats(100)
    pstats.Stats(profiler).sort_stats(pstats.SortKey.CUMULATIVE).dump_stats(filename)
