
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

    all_files = (rules_file, config_file, remotes_file)

    def __init__(self, repository, path):
        self.path = path
        self.repository = repository

    def create_files(self, **kws):
        # Write out default configs for all files that dont exist
        for relpath in self.all_files:
            path = os.path.join(self.path, relpath)
            if not os.path.exists(path):
                self.save_file(relpath, self.get_default(relpath, kws))


    def get_default_rules(self, kws = {}):
        return { 'rules': [] }

    def get_default_config(self, kws = {}):
        new_repo_id = str(uuid.uuid1())
        return {
            'id': new_repo_id,
            'nickname': kws.get('nickname', '{}-{}'.format(
                os.path.basename(self.repository.location), socket.gethostname()
                )),
            }

    def get_default_remotes(self, kws = {}):
        myid = self.repository.id()
        return {
            myid: {
                'uri': '.',
                'nickname': self.repository.nickname(),
                }
            }

    def get_default(self, relpath, kws = {}):
        return {
                self.rules_file: self.get_default_rules,
                self.config_file: self.get_default_config,
                self.remotes_file: self.get_default_remotes,
            }[relpath](kws)

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

    def get_rule(self, fn):
        return self.get_rules().get_rule(self.repository, fn)

    def get_rules(self):
        j = self.load_file(self.rules_file)
        rs = [Rule(**r) for r in j.get('rules', [])]

        rs.append(Rule(match_filename = '.harmony/*', ignore = True))
        rs.append(Rule(match_filename = '*'))
        return Ruleset(rs)

    def get_remotes(self):
        remotes = self.load_file(self.remotes_file)
        return remotes

    def set_remotes(self, remotes):
        self.save_file(self.remotes_file, remotes)

    def get_config(self, property_):
        configuration = self.load_file(self.config_file)
        return configuration[property_]


# vim: set ts=4 sw=4 expandtab:
