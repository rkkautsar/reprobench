#!/usr/bin/env python

import argparse
from loguru import logger
import sys
import strictyaml

from reprobench.core.schema import schema
from reprobench.utils import import_class


def run():
    parser = argparse.ArgumentParser(
        description="Run a benchmark based on configuration."
    )
    parser.add_argument("--runner", default="reprobench.runners.LocalRunner")
    parser.add_argument("-s", "--silent", help="Remove logging", action="store_true")
    parser.add_argument(
        "-v", "--verbose", help="Print lots of debugging messages", action="store_true"
    )
    parser.add_argument(
        "-vv",
        "--very-verbose",
        help="Print even more of debugging messages",
        action="store_true",
    )
    parser.add_argument("config", type=open)
    args = parser.parse_args()
    logger.remove()

    logger.add(sys.stderr, level="INFO")

    if args.silent:
        logger.remove()
    elif args.very_verbose:
        logger.remove()
        logger.add(sys.stderr, level="TRACE")
    elif args.verbose:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")

    config_text = args.config.read()
    config = strictyaml.load(config_text, schema=schema).data
    Runner = import_class(args.runner)
    runner = Runner(config)
    runner.run()

