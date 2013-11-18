
import os
import sys
from repository import Repository
import logging
import argparse

def cmd_info(repo):
	print('repository {}\nnickname {}\nHEAD {}'.format(
		repo.get_repository_id(),
		repo.get_repository_nickname(),
		repo.get_head_id()))
	
def run_command(args):
	
	commands = {
		'init': lambda args: repository.init(),
		'commit': lambda args: repository.commit(),
		'clone': lambda args: repository.clone(**args),
		'whereis': lambda args: repository.whereis(**args),
		'get': lambda args: repository.get(**args),
	}
	
	parser = argparse.ArgumentParser(description = 'Harmony')
	#parser.add_argument('command', metavar='command',
			#choices = commands.keys())
	parser.add_argument('--harmony-dir',
			help='harmony directory to operate on, defaults to working dir',
			default='.')
	subparsers = parser.add_subparsers()
	
	p_init = subparsers.add_parser('init', help='create a new repository')
	p_init.add_argument('--name', default=None, required=False)
	p_init.set_defaults(func=Repository.init, func_args=['name'])
	
	p_commit = subparsers.add_parser('commit', help='record current repository state')
	p_commit.set_defaults(func=Repository.commit, func_args=[])
	
	p_clone = subparsers.add_parser('clone', help='create a repository that is logically connected to an existing one')
	p_clone.add_argument('uri', help='URI of the repository to clone')
	p_clone.set_defaults(func=Repository.clone, func_args=['uri'])
	
	p_whereis = subparsers.add_parser('whereis', help='output a list of locations for a given file')
	p_whereis.add_argument('filename')
	p_whereis.set_defaults(func=Repository.whereis, func_args=['filename'])
	
	p_get = subparsers.add_parser('get', help='get current version of given file into this repository')
	p_get.add_argument('filename')
	p_get.set_defaults(func=Repository.get, func_args=['filename'])
	
	p_pull_state = subparsers.add_parser('pull-state', help='pull state from all available remotes')
	p_pull_state.add_argument('remote', help='ID or nickname of the remote to pull from')
	p_pull_state.set_defaults(func=Repository.pull_state, func_args=['remote'])
	
	p_log = subparsers.add_parser('log', help='list commits')
	p_log.set_defaults(func=Repository.cmd_log, func_args=[])
	
	p_info = subparsers.add_parser('info', help='info about repo')
	p_info.set_defaults(func=cmd_info, func_args=[])
	
	ns = parser.parse_args(args)
	repository = Repository(ns.harmony_dir)
	ns.func(repository, *[getattr(ns, v) for v in ns.func_args])
	
	#{
			#'init': lambda args: repository.init(),
			#'commit': lambda args: repository.commit(),
			#'clone': lambda args: repository.clone(args[0]),
			#'whereis': lambda args: repository.whereis(args[0]),
			#'get': lambda args: repository.get(args[0]),
	#}.get(args[0])(args[1:])

