
from rule import Rule

class Ruleset:

    def __init__(self, rules):
        self.rules = rules

    def get_rule(self, repository, fn):
        for r in self.rules:
            if r.match(repository, fn):
                return r
        return None

# vim: set ts=4 sw=4 expandtab:
