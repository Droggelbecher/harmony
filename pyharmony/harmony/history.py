
import os
import os.path
import hashlib
import datetime
import logging

from harmony import protocols
from harmony.commit import Commit
from harmony import serialization
from harmony.location_state import LocationState

class History:

    LOCATION_STATE_SUBDIR = 'location_states'

    @classmethod
    def init(class_, harmony_directory):
        """
        Create a new history, within the given harmony directory.
        """
        states_directory = os.path.join(harmony_directory, class_.LOCATION_STATE_SUBDIR)
        os.mkdir(states_directory)
        h = History(harmony_directory)
        return h

    @classmethod
    def load(class_, harmony_directory):
        h = History(harmony_directory)
        return h

    def __init__(self, harmony_directory):
        self.harmony_directory = harmony_directory
        self.states_directory = os.path.join(harmony_directory, History.LOCATION_STATE_SUBDIR)

    def create_state(self, location):
        try:
            s = self.read_state(location)
        except FileNotFoundError:
            s = None

        return s if s is not None else LocationState(location = location)

    def read_state(self, location):
        #s = serialization.read(os.path.join(self.states_directory, location))
        return LocationState.load(os.path.join(self.states_directory, location))

    def write_state(self, s):
        s.write(os.path.join(self.states_directory, s.location))


