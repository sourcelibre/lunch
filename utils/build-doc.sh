#!/bin/bash

# 
# Builds the HTML documentation for the Lunch Python package.
# 

epydoc  \
    --html \
    --output html \
    --url "http://svn.sat.qc.ca/trac/lunch" \
    --name "Lunch distributed process launcher" \
    --verbose \
    --simple-term \
    --css white lunch 
