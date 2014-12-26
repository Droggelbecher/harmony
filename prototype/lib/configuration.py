
import json
import os
import os.path
from ruleset import Ruleset
from rule import Rule
import socket
import uuid

class Configuration:

    rules_file = 'rules'
    config_file = 'config'
    remotes_file = 'remotes'

    def __init__(self, repository, path):
        self.path = path
        self.repository = repository

    def get_default_rules(self):
        return { 'rules': [] }

    def get_default_config(self):
        new_repo_id = str(uuid.uuid1())
        return {
            'id': new_repo_id,
            'nickname': '{}-{}'.format(
                os.path.basename(self.repository.location), socket.gethostname()
                )
            }

    def get_default_remotes(self):
        myid = self.repository.get_id()
        return {
            myid: {
                'uri': '.',
                'nickname': self.repository.get_nickname(),
                }
            }

    def get_default(self, relpath):
        return {
                rules_file: self.get_default_rules,
                config_file: self.get_default_config,
                remotes_file: self.get_default_remotes,
            }[relpath]()

    def load_file(self, relpath):
        path = os.path.join(self.path, relpath)
        if not os.path.exists(path):
            return self.get_default(relpath)
        with open(path, 'r') as f:
            configuration = json.load(f)
        return configuration

    def save_file(self, relpath, configuration):
        path = os.path.join(self.path, relpath)
        with open(path, 'w') as f:
            json.dump(configuration, f)

    def get_rule(self, repository, fn):
        return self.get_rules().get_rule(repository, fn)

    def get_rules(self):
        j = self.load_file(rules_file)
        rs = [Rule(**r) for r in j.get('rules', [])]

        rs.append(Rule(match_filename = '.harmony/*', ignore = True))
        rs.append(Rule(match_filename = '*'))
        return Ruleset(rs)

    def get_config(self, property_):
        configuraton = load_file(self, config_file)
        return configuration[property_]


# vim: set ts=4 sw=4 expandtab:
