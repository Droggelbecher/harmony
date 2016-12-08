
import os
import glob
import logging

from harmony import serialization

logger = logging.getLogger(__name__)

class HarmonyComponent:

    @classmethod
    def get_path(class_, harmony_directory):
        return os.path.join(harmony_directory, class_.RELATIVE_PATH)

    @classmethod
    def init(class_, path):
        r = class_(path)
        r.save()
        return r

    @classmethod
    def from_dict(class_, d):
        r = class_(**d)
        r._serialization_keys = sorted(list(set(d.keys()) - set(['path'])))
        return r

    def __init__(self, path):
        self.path = path

class DirectoryComponent(HarmonyComponent):

    @classmethod
    def init(class_, path):
        os.mkdir(path)
        r = super(DirectoryComponent, class_).init(path)
        return r

    @classmethod
    def item_from_dict(class_, d):
        return d

    @classmethod
    def load(class_, path):
        items = {

            filename: class_.item_from_dict(serialization.read(os.path.join(path, filename)))
            for filename in os.listdir(path)
        }
        return class_.from_dict({
            'path': path,
            'items': items
        })

    def __init__(self, path, items):
        self.path = path
        self.items = items

    def item_to_dict(self, item):
        return item

    def to_dict(self):
        return {
            'path': self.path,
            'items': { k: self.item_to_dict(v) for k, v in self.items.items() },
        }

    def save(self):
        d = self.to_dict()
        for filename, v in d['items'].items():
            serialization.write(v, os.path.join(self.path, filename))


class FileComponent(HarmonyComponent):

    @classmethod
    def load(class_, path):
        d = serialization.read(path)
        d['path'] = path
        return class_.from_dict(d)


    def save(self):
        d = self.to_dict()
        logger.debug('{}.to_dict = {}'.format(self, d))
        serialization.write(self.to_dict(), self.path)

