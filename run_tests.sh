#!/bin/bash

set -e

pipenv run mypy --ignore-missing-imports harmony
pipenv run pytest
