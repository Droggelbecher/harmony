
import os.path
import shutil
import glob
import logging
from pathlib import Path
import re
from collections import namedtuple
import tempfile

from paramiko import SSHClient, AutoAddPolicy
from scp import SCPClient

logger = logging.getLogger(__name__)

class ProtocolMeta(type):
    def __init__(class_, name, bases, dict_):
        if not hasattr(class_, 'registry'):
            class_.registry = {}
        else:
            id_ = name.lower()
            if id_.endswith('protocol'):
                id_ = id_[:-len('protocol')]
            class_.registry[id_] = class_
            logger.debug('registered protocol "{}" -> {}'.format(id_, class_.__name__))

        super().__init__(name, bases, dict_)

class Protocol(metaclass = ProtocolMeta):

    __slots__ = (
        'location'
        )

    def __init__(self, uri):
        self.address = self.parse_uri(uri)

    @classmethod
    def connect(class_, uri):
        assert isinstance(uri, str) or isinstance(uri, Path)
        uri = str(uri)
        for protocol in sorted(class_.registry.values(), key = lambda x: x.priority):
            if protocol.is_valid(uri):
                return protocol(uri)
        return None

class FileProtocol(Protocol):

    priority = 1000
    Address = Path

    @classmethod
    def is_valid(class_, uri):
        if uri == '/':
            return False
        address = class_.parse_uri(uri)
        return address.is_dir()

    @classmethod
    def parse_uri(_, uri):
        """
        Return a normalized version of the passed location,
        assuming this location is a valid location for this protocol.
        Else the return value might be a nonsensical string.
        """
        uri = str(uri)
        if uri.startswith('file://'):
            uri = uri[len('file://'):]
        return Path(uri).resolve()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, trackeback):
        pass

    def pull_harmony_files(self, paths):
        return {p: self.address / p for p in paths}

    def pull_working_files(self, paths, working_directory):
        working_directory = Path(working_directory)
        for path in paths:
            shutil.copyfile(str(self.address / path), str(working_directory / path))
        return {p: working_directory / p for p in paths}



class ScpProtocol(Protocol):

    uri_re = 'ssh://((?P<user>[^:@]+)?(?P<cpasswd>:[^:@]+)?@)?(?P<host>[^:/]+)(?P<path>.+)?'
    Address = namedtuple('SSHAddress', ['user', 'password', 'host', 'path'])
    priority = 500

    @classmethod
    def is_valid(class_, uri):
        return class_.parse_uri(uri) is not None

    @classmethod
    def parse_uri(class_, uri):
        m = re.match(class_.uri_re, uri)
        if m is None:
            return None

        d = m.groupdict()
        return class_.Address(
            user = d['user'],
            password = d['cpasswd'][1:] if d['cpasswd'] is not None else None,
            host = d['host'],
            path = d['path'][1:] if d['path'] is not None else None,
            )

    def abspath(self, p):
        if self.address.path is None:
            return p
        return self.address.path + '/' + p

    def __init__(self, uri):
        super().__init__(uri)
        if self.address is None:
            raise ValueError('Could not interpret "{}" as an SSH address.'.format(uri))

    def __enter__(self):
        self.ssh = SSHClient()
        self.ssh.load_system_host_keys()
        self.ssh.set_missing_host_key_policy(AutoAddPolicy())
        self.ssh.connect(self.address.host)
        self.scp = SCPClient(self.ssh.get_transport()).__enter__()
        self.tempdir = None
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.scp.__exit__(exc_type, exc_value, traceback)
        if self.tempdir is not None:
            self.tempdir.__exit__(exc_type, exc_value, traceback)

    # TODO: TBD: join into one function w/ working_directory optional?
    #       Implementation is after all relatively similiar in general...
    #       Also the names don't reflect the behavior well: pull_temporary / pull_permanently would be better
    def pull_harmony_files(self, paths):
        r = {}
        self.tempdir = tempfile.TemporaryDirectory()
        tempdir_name = Path(self.tempdir.__enter__())
        for p in paths:
            r[p] = tempdir_name / p
            logger.debug('scp({}, {})'.format(
                self.abspath(p), str(r[p])
                ))
            r[p].parent.mkdir(parents = True, exist_ok = True)
            self.scp.get(self.abspath(p), str(r[p]))
        return r

    def pull_working_files(self, paths, working_directory):
        r = {}
        for p in paths:
            source = self.abspath(p)
            destination = working_directory / p
            self.scp.get(source, str(destination))
            r[source] = destination
        return r



        

connect = Protocol.connect

