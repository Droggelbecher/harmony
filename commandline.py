
import os
import sys
from repository import Repository
import logging

def run_command(args):
	repository = Repository(os.getcwd())
	
	{
			'init': lambda args: repository.init(),
			'commit': lambda args: repository.commit(),
			'clone': lambda args: repository.clone(args[0]),
			'whereis': lambda args: repository.whereis(args[0]),
			'get': lambda args: repository.get(args[0]),
	}.get(args[0])(args[1:])

