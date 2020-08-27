#!/usr/bin/env python3

def str_to_bytes(value):
    return bytes(value, encoding='ascii')


def bytes_to_str(value):
    return value.decode('ascii')

