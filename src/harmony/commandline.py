#!/usr/bin/env python3

import os
import sys
import argparse
import logging

import harmony
from harmony.repository import Repository

class Command:
    def add_to_parser(self, subparsers):
        p = subparsers.add_parser(self.command, help = self.help)
        p.set_defaults(obj = self)
        self.setup_parser(p)

    def setup_parser(self, p):
        pass

    def make_repository(self, ns):
        return Repository.find(ns.cwd)


class InitCommand(Command):
    command = 'init'
    help = 'create a new repository'

    def setup_parser(self, p):
        p.add_argument('--name', default = None, required = False)

    def execute(self, ns):
        Repository.init(
                working_directory = ns.cwd,
                name = ns.name
                )

class CommitCommand(Command):
    command = 'commit'
    help = 'record current repository state into history'

    def execute(self, ns):
        r = self.make_repository(ns)
        r.commit()

class PullStateCommand(Command):
    command = 'pull-state'
    help = 'pull state from given remote or all that are available'

    def setup_parser(self, p):
        p.add_argument('remotes', nargs = '+', help = 'remote(s) to pull from, defaults to all known')

    def execute(self, ns):
        r = self.make_repository(ns)
        r.pull_state(remote_specs = ns.remotes)

class CloneCommand(Command):
    command = 'clone'
    help = 'create a repository that is logically connected to an existing one'

    def setup_parser(self, p):
        p.add_argument('location', help = 'location of the repository to clone')

    def execute(self, ns):
        r = Repository.clone(
                working_directory = ns.cwd,
                location = ns.location
                )

class PullFileCommand(Command):
    command = 'pull-file'
    help = 'get current version of given file into this repository'

    def setup_parser(self, p):
        p.add_argument('path', help = 'path of file (relative to repository root)')

    def execute(self, ns):
        r = self.make_repository(ns)
        r.pull_file(ns.path)

def run_command(args):
    commands = (
            InitCommand(),
            CommitCommand(),
            CloneCommand(),
            PullStateCommand(),
            PullFileCommand()
            )

    parser = argparse.ArgumentParser(description = 'Harmony')

    parser.add_argument('-C',
            dest = 'cwd',
            help = 'Run as if Harmony was started in this directory instead of current',
            default = os.getcwd()
            )

    subparsers = parser.add_subparsers()

    for command in commands:
        command.add_to_parser(subparsers)

    ns = parser.parse_args(args)
    if hasattr(ns, 'obj'):
        ns.obj.execute(ns)

    else:
        print(parser.format_help())


if __name__ == '__main__':
    logging.basicConfig(level = logging.WARN, format = '{levelname:7s}: {message:s} (in: {module:s}.{funcName:s}())', style = '{')
    run_command(sys.argv[1:])

