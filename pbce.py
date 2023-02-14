#! /usr/bin/env python3


class CustomException(Exception):
    def __init__(self, message):
        super().__init__()
        self.message = message

