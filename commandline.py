
import os
import sys
from repository import Repository

def run_command(args):
	repository = Repository(os.getcwd())
	
	{
			'init': lambda: repository.init(),
			'commit': lambda: repository.commit(),
	}.get(args[0])()

