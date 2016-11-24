
import os
import glob

from harmony import serialization

class HarmonyComponent:

    @classmethod
    def get_path(class_, harmony_directory):
        return os.path.join(harmony_directory, class_.RELATIVE_PATH)

    @classmethod
    def init(class_, path):
        r = class_(path)
        r.write()
        return r

    @classmethod
    def load(class_, path):
        r = class_(path)
        r.read(path)
        return r

    def __init__(self, path):
        self.path = path
        self.state = {}



class DirectoryComponent(HarmonyComponent):

    @classmethod
    def init(class_, path):
        os.mkdir(path)
        r = super(DirectoryComponent, class_).init(path)
        return r

    def read(self, path):
        self.state = {}
        for filename in glob.glob(os.path.join(path, '*')):
            self.state[filename] = self.read_item(os.path.join(path, filename))

    def read_item(self, path):
        return serialization.read(path)

    def write(self):
        for k, v in self.state.items():
            self.write_item(v, k)

    def write_item(self, data, path):
        serialization.write(v, k)

class FileComponent(HarmonyComponent):

    def read(self, path):
        self.state = serialization.read(path)

    def write(self):
        serialization.write(self.state, self.path)
