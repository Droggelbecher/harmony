
import shutil
import logging
from pathlib import Path
import re
from collections import namedtuple
import tempfile
from typing import Union, Iterable, Dict

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

    URI = Union[str, Path]

    def __init__(self, uri: URI) -> None:
        self.address = self.parse_uri(uri)

    @classmethod
    def parse_uri(self, uri: URI) -> str:
        """
        Given a URI that is assumed to be valid for this protocol, return a
        normalized version for internal use.  Two URIs pointing to the same
        thing should lead (if possible) to the same return value.

        Derived classes must implement this.
        """
        raise NotImplementedError

    @classmethod
    def connect(class_, uri: URI):
        uri = str(uri)
        for protocol in sorted(class_.registry.values(), key=lambda x: x.priority):
            if protocol.is_valid(uri):
                return protocol(uri)
        raise ValueError(f'No protocol found to connect to "{uri}".')

    def __enter__(self):
        """
        Open the connection.
        Must be implemented by derived class.
        """
        raise NotImplementedError

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Close the connection.
        Must be implemented by derived class.
        """
        raise NotImplementedError

    def pull_harmony_files(self, paths: Iterable[Path]) -> Dict[Path, Path]:
        """
        Shall only be executed on a currently open connection.  Given an
        iterable of paths relative to the harmony working directory, download
        the pointed to files to some local storage.

        The protocol is responsible for cleaning up these files
        (eg. during __exit__).

        Return a dict mapping requested relative path to path of stored file.

        Must be implemented by derived class.
        """
        raise NotImplementedError

    def pull_working_directory_files(self, paths: Iterable[Path], working_directory: Path) \
        -> Dict[Path, Path]:
        """
        Given a list of paths relative to the working directory
        and a local working directory path, download the requested files
        to the local working directory (with same relative paths).
        """
        raise NotImplementedError

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
    def parse_uri(class_, uri):
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
            user=d['user'],
            password=d['cpasswd'][1:] if d['cpasswd'] is not None else None,
            host=d['host'],
            path=d['path'][1:] if d['path'] is not None else None,
            )

    def abspath(self, p):
        if self.address.path is None:
            return p
        return self.address.path + '/' + p

    def __init__(self, uri):
        super().__init__(uri)
        if self.address is None:
            raise ValueError('Could not interpret "{}" as an SSH address.'.format(uri))
        self.scp = None
        self.tempdir = None

    def __enter__(self):
        ssh = SSHClient()
        ssh.load_system_host_keys()
        ssh.set_missing_host_key_policy(AutoAddPolicy())
        ssh.connect(self.address.host)
        self.scp = SCPClient(ssh.get_transport()).__enter__()
        self.tempdir = None
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.scp.__exit__(exc_type, exc_value, traceback)
        self.scp = None
        if self.tempdir is not None:
            self.tempdir.__exit__(exc_type, exc_value, traceback)

    def pull_harmony_files(self, paths):
        r = {}
        self.tempdir = tempfile.TemporaryDirectory()
        tempdir_name = Path(self.tempdir.__enter__())
        for p in paths:
            r[p] = tempdir_name / p
            logger.debug('scp({}, {})'.format(
                self.abspath(p), str(r[p])
                ))
            r[p].parent.mkdir(parents=True, exist_ok=True)
            self.scp.get(self.abspath(p), str(r[p]))
        return r

    def pull_working_files(self, paths, working_directory):
        for p in paths:
            source = self.abspath(p)
            destination = working_directory / p
            self.scp.get(source, str(destination))



connect = Protocol.connect

