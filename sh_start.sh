#!/bin/bash

PYTHONPATH=${PWD}:${PYTHONPATH} \
    PATH=${PATH}:${PWD}/scripts \
    ./scripts/lunch -g -v examples/simple.lunch

