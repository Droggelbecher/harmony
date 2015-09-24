
import copy
import datetime

class Commit:

    # This is not exactly ISO 8601, but close.
    # Unfortunately datetime can't parse its own .isoformat() output
    # (d'oh!)
    DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%f'

    def __init__(self, parents = ()):
        self.parents = parents
        self.created = datetime.datetime.utcnow()
        self.files = {}
        self.repositories = {}

    def update_repositories(self, commit):
        for id_, repository in commit.repositories.items:
            if id_ not in self.repositories or repository['revision'] > self.repositories['id']['revision']:
                self.repositories[id_] = copy.deepcopy(repository)

    def update_repository(self, repository, files):
        rid = repository.get_id()
        if rid not in self.repositories:
            self.repositories[rid] = dict()

        self.repositories[rid].update({
            'id': rid,
            'name': repository.get_name(),
            'files': copy.deepcopy(files)
            })

    def inherit_files(self, commit):
        """
        @param filename filename relative to repository
        @param commit commit to inherit from
        """
        self.files.update(commit.files)

    def update_file(self, filename, digest):
        self.files[filename] = digest

    def get_file(self, filename):
        return self.files.get(filename, None)



