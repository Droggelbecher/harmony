
import shutil
import os
import os.path
import logging

import protocol

class FileProtocol:
    name = 'file'
    
    def __init__(self):
        pass

    def is_writeable(self, uri):
        return True
    
    def to_dir(self, uri, remote_relative_path):
        #return os.path.join(uri.split(':')[1], remote_relative_path)
        return os.path.abspath(os.path.join(protocol.split_uri(uri)[1], remote_relative_path))
    
    def receive_file(self, uri, remote_relative_path, local_absolute_path):
        logging.debug("cp {} -> {}".format(self.to_dir(uri, remote_relative_path),
                local_absolute_path))
        shutil.copyfile(self.to_dir(uri, remote_relative_path), local_absolute_path)
        
    def receive_recursive(self, uri, remote_relative_path, local_absolute_path):
        shutil.copytree(self.to_dir(uri, remote_relative_path), local_absolute_path)

    def send_file(self, local_absolute_path, uri, remote_relative_path):
        logging.debug("cp {} -> {}".format(local_absolute_path, self.to_dir(uri, remote_relative_path)))
        shutil.copyfile(local_absolute_path, self.to_dir(uri, remote_relative_path))

    def send_recursive(self, local_absolute_path, uri, remote_relative_path):
        shutil.copytree(local_absolute_path, self.to_dir(uri, remote_relative_path))

    def append_file(self, uri, remote_relative_path, line):
        fn = self.to_dir(uri, remote_relative_path)
        with open(fn, 'a') as f:
            f.write(line + '\n')

protocol.register_protocol(FileProtocol())

