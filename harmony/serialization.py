
import logging

logger = logging.getLogger(__name__)

import yaml
from pathlib import Path, PosixPath

def read(filename):
    filename = str(filename)
    r = None
    with open(filename, 'r') as f:
        s = f.read()
        r = yaml.safe_load(s)
    return r

def write(d, filename):
    filename = str(filename)
    with open(filename, 'w') as f:
        logger.debug('  (-> {}): {}'.format(filename, d))
        yaml.safe_dump(d, f)

def dump(d):
    return yaml.safe_dump(d)


class Serializable(object):

    @classmethod
    def get_path(class_, harmony_directory):
        return Path(harmony_directory) / class_.RELATIVE_PATH

    @classmethod
    def init(class_, path):
        """
        Create new instance in the given path and write it to disk.
        """
        r = class_(path)
        r.save()
        return r

    @classmethod
    def from_dict(class_, d):
        """
        Construct instance from dict and return.
        """
        r = class_(**d)
        return r

    @classmethod
    def prepare_value_for_dict(class_, k, v):
        if isinstance(v, (Path, PosixPath)):
            v = str(v)

        if isinstance(k, (Path, PosixPath)):
            k = str(k)

        if hasattr(v, 'to_dict'):
            v = v.to_dict()
        elif isinstance(v, dict):
            v = dict(class_.prepare_value_for_dict(k_, v_) for k_, v_ in v.items())
        return k, v

    #@classmethod
    #def prepare_value_for_object(class_, k, v):
    #    return k, v

    def to_dict(self, skip = ()):
        if hasattr(self, '_state'):
            keys = set(self._state)
        elif hasattr(self, '__slots__'):
            keys = set(k for k in self.__slots__ if not k.startswith('_'))
        else:
            keys = set(k for k in self.__dict__.keys() if not k.startswith('_'))

        keys = keys - set(skip)

        return dict(
            self.prepare_value_for_dict(k, getattr(self, k))
            for k  in keys
            )

    def __init__(self, path):
        self.path = Path(path) if path is not None else None


class DirectorySerializable(Serializable):

    @classmethod
    def init(class_, path):
        path = Path(path)
        path.mkdir()
        return super().init(path)

    @classmethod
    def load(class_, path):
        path = Path(path)
        items = {
            filename.name: read(filename)
            for filename in path.iterdir() if not str(filename).startswith('.')
            }
        return class_.from_dict({
            'path': path,
            'items': items,
            })

    @classmethod
    def from_dict(class_, d):
        items = { k: class_.item_from_dict(v) for k, v in d['items'].items() }
        d['items'] = items
        return super().from_dict(d)

    def to_dict(self):
        d = super().to_dict(skip = ('items',))
        d['items'] = { k: self.item_to_dict(v) for k, v in self.items.items() }
        return d

    @classmethod
    def item_from_dict(class_, d):
        return class_.Item.from_dict(d)

    def item_to_dict(self, item):
        return item.to_dict()

    def __init__(self, path, items):
       super().__init__(path)
       self.items = items

    def save(self):
        d = self.to_dict()
        for k, v in d['items'].items():
            p = Path(self.path) / k
            logger.debug('SAVE {} -> {}'.format(v, p))
            write(v, p)

class FileSerializable(Serializable):

    @classmethod
    def load(class_, path):
        path = Path(path)
        d = read(path)
        d['path'] = Path(path)
        return class_.from_dict(d)

    def __init__(self, path):
        super().__init__(path)

    def save(self):
        d = self.to_dict()
        if 'path' in d:
            del d['path']
        write(d, self.path)


