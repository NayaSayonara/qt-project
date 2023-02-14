#! /usr/bin/env python3

#from __future__ import print_function
from threading import Lock
import time
from datetime import datetime
import logging
import logging.handlers
import inspect
import builtins as __builtin__
from traceback import print_exc
import io
import platform

import pbglobals as pbg


print_lock = Lock()


def print(*args, **kwargs):
    logging_levels = {
        'debug': pbg.logger.debug,
        'info': pbg.logger.info,
        'warning': pbg.logger.warning,
        'error': pbg.logger.error,
        'critical': pbg.logger.critical,
        'exception': pbg.logger.exception
    }
    
    if pbg.start_time is None:
        pbg.start_time = time.time()

    with print_lock:
        if 'logl' in kwargs:
            loglevel = kwargs['logl']
            del kwargs['logl']
        else:
            loglevel = 'debug'
        output = io.StringIO()
        __builtin__.print("%.4f %s() " % (time.time() - pbg.start_time,
                                          inspect.currentframe().f_back.f_code.co_name), file=output, end='')
        __builtin__.print(*args, file=output, end='', **kwargs)
        contents = output.getvalue()

        logging_levels[loglevel](contents)
        output.close()

