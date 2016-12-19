#!/usr/bin/env python3

import os
import sys
import argparse
import logging

import harmony
from harmony.repository import Repository

class Command:
    aliases = ()

    def add_to_parser(self, subparsers):
        for cmd in [self.command] + list(self.aliases):
            p = subparsers.add_parser(cmd, help = self.help)
            self.parser = p
            p.set_defaults(obj = self)
            self.setup_parser(p)

    def setup_parser(self, p):
        pass

    def make_repository(self, ns):
        return Repository.find(ns.cwd)

    def run(self, parser, ns):
        return self.execute(ns)

class CommandGroup:
    aliases = ()
    commands = ()

    def add_to_parser(self, subparsers):
        for cmd in [self.command] + list(self.aliases):
            p = subparsers.add_parser(cmd, help = self.help)
            self.parser = p
            p.set_defaults(obj = self)
            self.setup_parser(p)

    def setup_parser(self, p):
        subparsers = p.add_subparsers()
        for command in self.commands:
            command.add_to_parser(subparsers)

    def make_repository(self, ns):
        return Repository.find(ns.cwd)

    def run(self, parser, ns):
        obj = None

        if hasattr(ns, 'obj'):
            if isinstance(ns.obj, list):
                obj = ns.obj.pop()
                if not ns.obj:
                    del ns.obj
            else:
                obj = ns.obj
                del ns.obj

        if obj is not None:
            return obj.run(parser, ns)
        else:
            print(self.parser.format_help())


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


class RemoteCommand(CommandGroup):
    command = 'remote'
    help = 'Manipulate the local directory of remote locations'

    class AddCommand(Command):
        command = 'add'
        help = 'add a remote location for convenient access'

        def setup_parser(self, p):
            p.add_argument('name', help = 'shorthand local name for this remote location')
            p.add_argument('url', help = 'URL of the remote')

        def execute(self, ns):
            r = self.make_repository(ns)
            r.add_remote(name = ns.name, location = ns.url)

    class RemoveCommand(Command):
        command = 'remove'
        aliases = ('rm', )
        help = 'remove a remote location by name'

        def setup_parser(self, p):
            p.add_argument('name', help = 'name of the remote to remove')

        def execute(self, ns):
            r = self.make_repository(ns)
            r.remove_remote(name = ns.name)

    class ListCommand(Command):
        command = 'list'
        aliases = ('ls', )
        help = 'list known remotes'

        def execute(self, ns):
            r = self.make_repository(ns)
            remotes = r.get_remotes()



    commands = (
        AddCommand(),
        RemoveCommand()
    )

def run_command(args):
    commands = (
        InitCommand(),
        CommitCommand(),
        CloneCommand(),
        PullStateCommand(),
        PullFileCommand(),
        RemoteCommand()
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
        ns.obj.run(parser, ns)

    else:
        print(parser.format_help())


if __name__ == '__main__':
    logging.basicConfig(level = logging.WARN, format = '{levelname:7s}: {message:s} (in: {module:s}.{funcName:s}())', style = '{')
    run_command(sys.argv[1:])

