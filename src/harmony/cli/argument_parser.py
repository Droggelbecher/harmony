#!/usr/bin/env python3

import os
import sys
import argparse
import logging

from harmony.cli.commands import COMMANDS

def run_command(args):

    parser = argparse.ArgumentParser(description = 'Harmony')

    parser.add_argument('-C',
            dest = 'cwd',
            help = 'Run as if Harmony was started in this directory instead of current',
            default = os.getcwd()
            )

    subparsers = parser.add_subparsers()
    for command in COMMANDS:
        command.add_to_parser(subparsers)

    ns = parser.parse_args(args)
    if hasattr(ns, 'obj'):

        try:
            ns.obj.run(parser, ns)
        except Exception as e:
            logging.error(e)
            sys.exit(1)

    else:
        print(parser.format_help())


if __name__ == '__main__':
    logging.basicConfig(level = logging.WARN, format = '{levelname:7s}: {message:s} (in: {module:s}.{funcName:s}())', style = '{')
    run_command(sys.argv[1:])

