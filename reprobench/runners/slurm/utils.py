from itertools import tee, zip_longest

# https://stackoverflow.com/a/3430312/9314778


def pairwise_longest(iterable):
    "variation of pairwise in http://docs.python.org/library/itertools.html#recipes"
    a, b = tee(iterable)
    next(b, None)
    return zip_longest(a, b)


def takeuntil(predicate, iterable):
    """returns all elements before and including the one for which the predicate is true
    variation of http://docs.python.org/library/itertools.html#itertools.takewhile"""
    for x in iterable:
        yield x
        if predicate(x):
            break


def get_range(it):
    "gets a range from a pairwise iterator"
    rng = list(takeuntil(lambda args: (args[1] is None) or (args[1] - args[0] > 1), it))
    if rng:
        b, e = rng[0][0], rng[-1][0]
        return "%d-%d" % (b, e) if b != e else str(b)


def create_ranges(zones):
    it = pairwise_longest(zones)
    return ",".join(iter(lambda: get_range(it), None))
