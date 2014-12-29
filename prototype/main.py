#!/usr/bin/env python3


import sys
import os
import os.path
sys.path.append(os.path.join(os.path.dirname(__file__), 'lib/'))

import logging
import protocols.file

import commandline

if __name__ == '__main__':
	logging.basicConfig(level = logging.DEBUG, format = '{message:s}', style = '{')
	
	commandline.run_command(sys.argv[1:])

