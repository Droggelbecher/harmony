
import os
import os.path
import hashlib
import datetime
import logging

from harmony import protocols
from harmony import serialization
from harmony.location_state import LocationState
from harmony.harmony_component import DirectoryComponent

class History(DirectoryComponent):

    RELATIVE_PATH = 'history'

    def __init__(self, path):
        super().__init__(path)
        self.state = {}

    def read(self, path):
        TODO

    def write(self):
        for location_state in self.location_states.values():
            self.write_state(location_state)

    def write_state(self, s):
        s.write(os.path.join(self.path, s.location))

    def create_state(self, location):
        try:
            s = self.read_state(location)
        except FileNotFoundError:
            s = None
        return s if s is not None else LocationState(location = location)

    #def read_state(self, location):
        ##s = serialization.read(os.path.join(self.states_directory, location))
        #return LocationState.load(os.path.join(self.states_directory, location))

