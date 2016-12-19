#!/usr/bin/env python3

from harmony.repository import Repository
from harmony.cli.command import Command, CommandGroup
from harmony.cli import console

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
            console.write_table(
                [(r.name, r.location) for r in remotes],
                #headers = ('Name', 'URL')
            )

    commands = (
        AddCommand(),
        RemoveCommand(),
        ListCommand()
    )


COMMANDS = (
    InitCommand(),
    CommitCommand(),
    CloneCommand(),
    PullStateCommand(),
    PullFileCommand(),
    RemoteCommand()
)


