
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

    def __hash__(self):
        return hash(self.created) \
                ^ hash(tuple(self.parents))
    #hash(self.files) \
                #^ hash(self.repositories) \

    def __eq__(self):
        return self.created == other.created \
                and self.parents == other.parents \
                and self.files == other.files \
                and self.repositories == other.repositories \

    def equal_state(self, other):
        """
        Two commits are considered equal wrt. state if they represent the same
        working dir / repository state.
        They may have different parents though and/or been created at
        different points in time.
        """
        # TODO: copying both dictonaries deeply just to ignore the revision
        # is not ideal
        sr = copy.deepcopy(self.repositories)
        for k, v in sr.items():
            del v['revision']

        or_ = copy.deepcopy(other.repositories)
        for k, v in or_.items():
            del v['revision']

        r = (self.files == other.files) and (sr == or_)
        #print("files=", self.files==other.files, "repos=",
                #self.repositories==other.repositories, "equal_state=", r)
        #print("self.repos=", self.repositories)
        #print("other.repos=", other.repositories)
        #print("self.files=", self.files)
        #print("other.files=", other.files)
        return r


    def __neq__(self, other):
        return not self.__eq__(other)

    def update_repositories(self, commit):
        for id_, repository in commit.repositories.items():
            if id_ not in self.repositories or repository['revision'] > self.repositories[id_]['revision']:
                self.repositories[id_] = copy.deepcopy(repository)

    def update_repository(self, repository, files):
        rid = repository.get_id()
        if rid not in self.repositories:
            self.repositories[rid] = dict()

        self.repositories[rid].update({
            'id': rid,
            'name': repository.get_name(),
            'files': copy.deepcopy(files),
            'revision': repository.revision,
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



