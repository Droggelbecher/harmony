
import os
import logging

import protocol
import os
import os.path

class Remote:
    def __init__(self, repository, remote_id, uri, nickname):
        self.remote_id = remote_id
        self.nickname = nickname
        self.uri = uri
        self.repository = repository
    
    def get_protocol(self):
        return protocol.find_protocol(self.uri)
    
    def pull_file(self, relpath):
        p = self.get_protocol()
        p.receive_file(self.uri, relpath, os.path.join(self.repository.location, relpath))

    def push_file(self, relpath):
        p = self.get_protocol()
        p.send_file(os.path.join(self.repository.location, relpath), self.uri, relpath)

    def push_history(self):
        p = self.get_protocol()
        history_dir = self.repository.commit_dir()
        p.send_recursive(history_dir, self.uri, '.harmony/history')

    def add_remote_head(self, new_head):
        p = self.get_protocol()
        p.append_file(self.uri, '.harmony/new_heads', str(new_head))

    def is_writeable(self):
        return self.get_protocol().is_writeable(self.uri)

    def __str__(self):
        return 'Remote(id={}, uri={}, nick={})'.format(self.remote_id,
                self.uri, self.nickname)
        
    @staticmethod
    def equivalent_uri(a, b):
        a_proto, a_uri = protocol.split_uri(a)
        b_proto, b_uri = protocol.split_uri(b)
        
        if a_proto == '': a_proto = protocol.DEFAULT_PROTOCOL
        if b_proto == '': b_proto = protocol.DEFAULT_PROTOCOL
        
        if a_proto != b_proto: return False
        
        logging.debug(os.path.abspath(a_uri))
        logging.debug(os.path.abspath(b_uri))
        
        return os.path.abspath(a_uri) == os.path.abspath(b_uri)
        
    
