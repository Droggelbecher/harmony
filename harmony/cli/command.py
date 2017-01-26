
from harmony.repository import Repository

class Command:
    aliases = ()

    def add_to_parser(self, subparsers):
        p = subparsers.add_parser(self.command, aliases = self.aliases, help = self.help)
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
        subparsers = p.add_subparsers(title = 'subcommands')
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

