
from tempfile import TemporaryDirectory
from pathlib import Path
import pytest
import logging

from harmony.protocols import ScpProtocol

logger = logging.getLogger(__name__)

@pytest.fixture(autouse = True)
def setup():
    logging.basicConfig(level = logging.DEBUG, format = '{levelname:7s} {module:15s}:{funcName:15s} | {message:s}', style = '{')

def test_scp_normalize():

    f = ScpProtocol.parse_uri
    A = ScpProtocol.Address

    assert f('ssh://foo:bar@host.edu.com/some/path') == A(
        user = 'foo',
        password = 'bar',
        host = 'host.edu.com',
        path = 'some/path'
        )

    assert f('ssh://foo@host.edu.com/some/path') == A(
        user = 'foo',
        password = None,
        host = 'host.edu.com',
        path = 'some/path'
        )

    assert f('ssh://some-other-host.eu//a/rooted/path') == A(
        user = None,
        password = None,
        host = 'some-other-host.eu',
        path = '/a/rooted/path'
        )

    assert f('ssh://justhost') == A(
        user = None,
        password = None,
        host = 'justhost',
        path = None
        )

#@pytest.mark.skip(reason = 'Depends on environment (local keybased SSH must be possible for running user)')
def test_scp_transfer_localhost():
    with TemporaryDirectory() as d:

        files = [
            'test.txt',
            'foo/foo.txt',
            'foo/test.txt'
            ]

        for filename in files:
            (Path(d) / filename).parent.mkdir(parents = True, exist_ok = True)
            logger.debug("Creating {}".format( Path(d) / filename ))
            (Path(d) / filename).write_text('This is the file {}'.format(filename))

        with ScpProtocol('ssh://127.0.0.1/' + d) as p:
            r = p.pull_harmony_files(files)
            assert set(r.keys()) == set(files)
            for k, v in r.items():
                assert (Path(d) / k).read_text() == Path(v).read_text()

