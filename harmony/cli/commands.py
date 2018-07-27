#!/usr/bin/env python3

import logging

from harmony.repository import Repository
from harmony.cli.command import Command, CommandGroup
from harmony.cli import console

class InitCommand(Command):
    command = 'init'
    help = 'create a new repository'

    def setup_parser(self, p):
        p.add_argument('--name', default=None, required=False)

    def execute(self, ns):
        Repository.init(working_directory=ns.cwd, name=ns.name)

class CommitCommand(Command):
    command = 'commit'
    help = 'record current repository state into history'

    def execute(self, ns):
        from tqdm import tqdm
        r = self.make_repository(ns)
        any_change = r.commit(
            Stats=lambda x: tqdm(
                total=x,
                unit='B',
                unit_scale=True,
                ncols=60,
            )
        )
        if not any_change:
            print('Nothing to commit.')

class PullStateCommand(Command):
    command = 'pull-state'
    help = 'pull state from given remote or all that are available'

    def setup_parser(self, p):
        p.add_argument('remote', help='remote to pull from')

    def execute(self, ns):
        r = self.make_repository(ns)
        r.pull_state(remote_spec=ns.remote)

class CloneCommand(Command):
    command = 'clone'
    help = 'create a repository that is logically connected to an existing one'

    def setup_parser(self, p):
        p.add_argument('location', help = 'location of the repository to clone')

    def execute(self, ns):
        Repository.clone(
            working_directory = ns.cwd,
            location = ns.location
        )

class StatusCommand(Command):
    command = 'status'
    aliases = ('st', )
    help = 'list working directory files for which a newer version is available'

    def execute(self, ns):
        logger = logging.getLogger(__name__)

        r = self.make_repository(ns)
        # 1. find all them outdated files and their recent digests
        # 2. find locations that have them and file sizes
        files = r.get_file_stats()
        logger.debug(f'file stats: {files}')

        def status(f):
            s = ' '
            if not f.exists_in_repository:
                s = '?'
            else:
                if f.exists_in_location_state:
                    if not f.exists_in_workdir:
                        s = 'D'
                    elif f.maybe_modified:
                        s = 'M'
                    else:
                        s = ' '
                else:
                    if f.exists_in_workdir:
                        # File is known in repository but was not expected in this location
                        # (didnt come here via 'hm get')
                        s = 'A'
                    else:
                        # file is currently ignored by this repository
                        s = 'i'

            s += ' ' if f.is_most_recent else 'O'
            return s

        def boring(f):
            return (
                f.exists_in_repository
                and f.exists_in_location_state
                and f.exists_in_workdir
                and not f.maybe_modified
                and f.is_most_recent
            )

        console.write_table([
            (status(f), path)
            for path, f in sorted(files.items())
            if not boring(f)
        ])

class GetCommand(Command):
    # TODO: Write test ensuring this gets the most recent version in the
    # presence of multiple versions

    command = 'get'
    help = 'get current version of given file into this repository'

    # TODO
    #     Think more about how the user interface of this should be like.
    #     This should rather look like
    #
    #     hm get [filename]
    #         Get the latest version from any available remote

    def setup_parser(self, p):
        p.add_argument('path', help='path of file (relative to repository root)')
        p.add_argument('remote_spec', help='Location to pull from')

    def execute(self, ns):
        r = self.make_repository(ns)
        r.pull_file(ns.path, ns.remote_spec)

class RemoteCommand(CommandGroup):
    command = 'remote'
    help = 'Manipulate the local directory of remote locations'

    class AddCommand(Command):
        command = 'add'
        help = 'add a remote location for convenient access'

        def setup_parser(self, p):
            p.add_argument('name', help='shorthand local name for this remote location')
            p.add_argument('url', help='URL of the remote')

        def execute(self, ns):
            r = self.make_repository(ns)
            r.add_remote(name=ns.name, location=ns.url)

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
        ListCommand(),
        AddCommand(),
        RemoveCommand(),
    )


COMMANDS = (
    InitCommand(),
    CommitCommand(),
    CloneCommand(),
    PullStateCommand(),
    StatusCommand(),
    GetCommand(),
    RemoteCommand()
)


