
from harmony import hashers
import os
import re
from harmony import serialization
import fnmatch

class Ruleset:

    RULES_FILE = 'rules'

    class FileInfo:
        pass

    @classmethod
    def init(class_, harmony_directory):
        r = class_(harmony_directory)

        r.add_rule(
                match = {},
                hasher = hashers.DEFAULT,
                commit = True,
                action = 'continue'
                )

        r.add_rule(
                match = {'path': '/.harmony/**'},
                commit = False,
                action = 'stop'
                )

        r.add_rule(
                match = {'filename': ['*.swp', '*.bak', '*~', '*.pyc']},
                commit = False,
                action = 'stop'
                )

        r.write()

        return r

    @classmethod
    def load(class_, harmony_directory):
        r = class_(harmony_directory)
        rules_data = serialization.read(r.rules_file)
        r.rules = rules_data['rules']
        assert len(r.rules) > 0

        return r

    @staticmethod
    def match_path(path, pattern):

        anchored = pattern.startswith('/')
        if anchored:
            pattern = pattern[1:]

        path_elements = path.split(os.path.sep)
        pattern_elements = pattern.split(os.path.sep)

        def match_recursive(i_pattern, i_path):
            if i_pattern >= len(pattern_elements):
                return i_path >= len(path_elements)
            e_pattern = pattern_elements[i_pattern]

            if i_path >= len(path_elements):
                return e_pattern != '**'

            e_path = path_elements[i_path]

            if e_pattern == '**':
                # If the pattern ended with **, everything that comes,
                # matches, so we are done
                if i_pattern == len(pattern_elements) - 1:
                    return True

                # No try all possible chains of subdirectories for '**'
                i = i_path
                while i < len(path_elements):
                    if match_recursive(i_pattern + 1, i):
                        return True
                    i += 1
                return False

            else:
                match = fnmatch.fnmatch(e_path, e_pattern)
                if not match:
                    return False
                return match_recursive(i_pattern + 1, i_path + 1)

        return match_recursive(0, 0)
        

         #TODO: this should more behave like rsyncs matching

        #pattern = pattern.replace('.', '\\.')
        #pattern = pattern.replace('?', '.')

        #pattern, _ = re.subn(r'(?<!\*)\*(?!\*)', '[^/]*', pattern)
        #pattern, _ = re.subn(r'\*\*', '.*', pattern)
        #pattern += '$'

        #m = re.match(pattern, path)
        #return m is not None

    @staticmethod
    def match_directory(path, pattern):
        path_elements = path.split(os.path.sep)
        for e in path_elements[:-1]:
            if fnmatch.fnmatch(e, pattern):
                return True
        return False

    @staticmethod
    def match_filename(path, pattern):
        path_elements = path.split(os.path.sep)

        if not isinstance(pattern, list):
            pattern = [pattern]

        for p in pattern:
            if fnmatch.fnmatch(path_elements[-1], p):
                return True
        return False

    def __init__(self, harmony_directory):
        self.harmony_directory = harmony_directory
        self.rules = []
        self.rules_file = os.path.join(self.harmony_directory, Ruleset.RULES_FILE)
        self.matchers = {
                'path': Ruleset.match_path,
                'dirname': Ruleset.match_directory,
                'filename': Ruleset.match_filename,
                }


    def iterate_committable_files(self, working_directory):
        for file_info in self.iterate_files(working_directory):
            if file_info.rule['commit']:
                yield file_info

    def iterate_files(self, working_directory):
        for root, dirs, files in os.walk(working_directory):
            for filename in files:
                absfn = os.path.join(root, filename)
                relfn = os.path.relpath(absfn, working_directory)
                rule = self.get_rule(relfn)

                file_info = Ruleset.FileInfo()
                file_info.absolute_filename = absfn
                file_info.relative_filename = relfn
                file_info.rule = rule

                yield file_info

    def get_rule(self, relfn):
        result = {
                'commit': True
                }
        for rule in self.rules:
            matches = True
            for matcher, parameters in rule['match'].items():
                if not self.matchers[matcher](relfn, parameters):
                    matches = False
                    break

            if matches:
                result.update(rule)
                if rule['action'] == 'continue':
                    continue
                break
        return result


    def add_rule(self, **kws):
        self.rules.append(kws)

    def write(self):
        d = {
                'rules': self.rules
                }
        serialization.write(d, self.rules_file)


