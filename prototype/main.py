#!/usr/bin/env python3


import sys
sys.path.append('lib/')

import logging
import protocols.file

import commandline

if __name__ == '__main__':
	logging.basicConfig(level = logging.INFO, format = '{message:s}', style = '{')
	
	commandline.run_command(sys.argv[1:])

