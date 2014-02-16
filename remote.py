
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
    
    def get(self, relpath):
        p = self.get_protocol()
        p.get_file(self.uri, relpath,
                os.path.join(self.repository.location, relpath))

    def is_writeable(self):
        return self.get_protocol().is_writeable(self.uri)
        
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
        
    
