
import shutil
import os
import os.path
import logging

import protocol

class FileProtocol:
    name = 'file'
    
    def __init__(self):
        pass
    
    def to_dir(self, uri, remote_relative_path):
        #return os.path.join(uri.split(':')[1], remote_relative_path)
        return os.path.join(protocol.split_uri(uri)[1], remote_relative_path)
    
    def get_file(self, uri, remote_relative_path, local_absolute_path):
        logging.debug("cp {} -> {}".format(self.to_dir(uri, remote_relative_path),
                local_absolute_path))
        shutil.copyfile(self.to_dir(uri, remote_relative_path), local_absolute_path)
        
    def get_recursive(self, uri, remote_relative_path, local_absolute_path):
        shutil.copytree(self.to_dir(uri, remote_relative_path), local_absolute_path)

    def append_file(self, uri, remote_relative_path, line):
        # TODO:
        # Idea: .harmony/copy_notices/ is a directory
        # with files whose name is somehow uniquely generated
        # (random UUID or hash of its content), files look like this:
        #
        # {
        #   "fetched_by": "d2769866-9696-11e3-84df-00252259448d",
        #   "created": "2014-02-17T07:44:34.994935",
        #   "parent_commit": "c0ab8616564fae976dabd860b72bd1cd9d6a705b1de4f408df466d717b564a3f",
        #   "files": {
        #       "blah.txt": {
        #           "content_id": "sha256:622cb3371c1a08096eaac564fb59acccda1fcdbe13a9dd10b486e6463c8c2525",
        #       }
        #   }
        # }
        #
        # This way, repo can be informed over a file get without complex remote state
        # transformations (i.e. no committing, no read-modify-write
        # transaction necessary, etc...).
        #
        # Repo just has to read in all those files on the next occasion
        # (i.e. should be checked before every command run) and turn into
        # commits.
        #
        # Drawback: this only works when the repo is "actively" being used,
        # not for transfer points. However on syncing we could even look at
        # these 
        #
        pass
    

protocol.register_protocol(FileProtocol())

