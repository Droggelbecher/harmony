
class RemoteRepository:

    def __init__(self, **kws):
        self.__dict__.update(kws)

    def get_id(self):
        return self.id_

    def get_name(self):
        return self.name


