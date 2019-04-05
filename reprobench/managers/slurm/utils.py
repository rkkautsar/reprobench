import subprocess
from itertools import groupby
from operator import itemgetter


def consecutive_groups(it):
    for _, g in groupby(enumerate(it), lambda tup: tup[0] - tup[1]):
        yield tuple(map(itemgetter(1), g))


def to_comma_range(it):
    return ",".join(
        "-".join(map(str, (g[0], g[-1])[: len(g)])) for g in consecutive_groups(it)
    )


def get_nodelist(job_step):
    """
    Blocks until job step is assigned a node
    """
    while True:
        cmd = ["sacct", "-n", "--parsable2", "-j", job_step, "-o", "NodeList"]
        output = subprocess.check_output(cmd)
        if len(output) > 0 and output != b"None assigned\n":
            return output.decode().strip()
