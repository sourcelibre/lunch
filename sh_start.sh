#!/bin/bash

PYTHONPATH=${PWD}:${PYTHONPATH} trial lunch \
    PATH=${PATH}:${PWD}/scripts \
    ./scripts/lunch -g -v examples/simple.lunch

