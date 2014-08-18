#!/usr/bin/env python3

import logging
import protocols.file

import commandline
import sys

if __name__ == '__main__':
	logging.basicConfig(level = logging.INFO, format = '{message:s}', style = '{')
	
	commandline.run_command(sys.argv[1:])

