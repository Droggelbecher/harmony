
import json
import os
import os.path
from ruleset import Ruleset
from rule import Rule

class Configuration:
    def __init__(self, path):
        self.path = path

    def get_json(self, relpath):
        path = os.path.join(self.path, relpath)
        if not os.path.exists(path):
            return {}
        with open(path, 'r') as f:
            obj = json.load(f)
        return obj

    def get_rule(self, repository, fn):
        return self.get_rules().get_rule(repository, fn)

    def get_rules(self):
        j = self.get_json('rules')
        rs = [Rule(**r) for r in j.get('rules', [])]

        rs.append(Rule(match_filename = '.harmony/*', ignore = True))
        rs.append(Rule(match_filename = '*'))
        return Ruleset(rs)

# vim: set ts=4 sw=4 expandtab:
