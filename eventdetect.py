#!/usr/bin/python
# -*- coding:utf-8 -*-

from logprint import print

import fcntl
import os
import queue
import select
import sys
import termios
import threading
import time
import serial

from utils import *

class EventDetect:
    
    def __init__(self, ev_exit, fd_key, fd_ser_, event_queue=None):
        self._ev_exit = ev_exit
        self._enabled = True
        self._fd_key = fd_key
        self._fd_ser = fd_ser_
        if event_queue is None:
            self._ev_queue = queue.Queue()
        else:
            self._ev_queue = event_queue

        # stream data input ot LF terminated blocks
        self._ser_readline = False
        # CRLF or just LF at the end if _ser_readline is set to true
        self._ser_writeline_crlf = False
        
        self._select_list = []
        if self._fd_key is not None:
            self._select_list.append(self._fd_key)
        if self._fd_ser is not None:
            self._select_list.append(self._fd_ser)

        self._oldterm = None
        
    
    def ser_readline(self):
        return self._ser_readline

    
    def set_ser_readline(self, state):
        self._ser_readline = state
        print("ser_readline set to ", self._ser_readline)

        
    def ser_writeline_crlf(self):
        return self._ser_writeline_crlf

    
    def set_ser_writeline_crlf(self, state):
        self._ser_writeline_crlf = state
        print("_ser_writeline_crlf set to ", self._ser_writeline_crlf)

        
    def check_event(self):
        event_type = None
        event_data = None

        rlist, a, a = select.select(self._select_list, [], [], 0.1)
        if self._fd_key in rlist:
            try:
                buf = sys.stdin.read(1)
            except IOError:
                print("IOError")
                buf = []
            finally:
                pass

            if len(buf) > 0:
                # print ("Read %d" % (len(buf)))
                event_data = buf[0]
                event_type = 'key'
            else:
                print("No Data Available")
        elif self._fd_ser in rlist:
            # print("Data Available from Ser")
            try:
                rx_data = bytearray(b'')
                if not self.ser_readline():
                    #rx_data.clear()
                    while self._fd_ser.in_waiting > 0:
                        #rx_data.append(self._fd_ser.read())
                        rx_data.extend(self._fd_ser.read())
                else:
                    rx_data = self._fd_ser.readline().rstrip()
                if rx_data:
                    #print('ser rx:')
                    #print_hex(rx_data)
                    event_data = bytes(rx_data)
                    event_type = 'ser'
            # except:
            except Exception as e_ser:
                print("Exception from Ser ", e_ser)
                print('type is:', e_ser.__class__.__name__)
                pass

        return event_type, event_data

    def event_reader_thread(self):
        # print("event_reader_thread started")

        # Make stdin non blocking
        if self._fd_key is not None:
            flags = fcntl.fcntl(self._fd_key, fcntl.F_GETFL)
            fcntl.fcntl(self._fd_key, fcntl.F_SETFL, flags | os.O_NONBLOCK)

            oldterm = termios.tcgetattr(self._fd_key)
            self._oldterm = oldterm

            newattr = termios.tcgetattr(self._fd_key)
            newattr[3] = newattr[3] & ~termios.ICANON & ~termios.ECHO
            termios.tcsetattr(self._fd_key, termios.TCSANOW, newattr)

        while self._enabled:
            # print("event_reader_thread calling check_event")
            evt_type, evt_data = self.check_event()
            if self._ev_exit.is_set():
                self._enabled = False
                print("event_reader_thread got shutdown evt")
                break
            if evt_type is None:
                continue
            # print("event_reader_thread check_event got ", evt_type, evt_data)
            self._ev_queue.put((evt_type, evt_data))

        print("event_reader_thread terminating...")
        # Make stdin blocking again. (needed?)
        if self._fd_key is not None:
            fcntl.fcntl(self._fd_key, fcntl.F_SETFL, flags)
            termios.tcsetattr(self._fd_key, termios.TCSAFLUSH, oldterm)

    def x_ser(self, tx_data=None, x_ser_timeout=None, flush_keys=True):
        rx_data = None
        key = None
        excp = None

        if tx_data is not None:
            # flush whatever events (objects) we had in 
            # queue - they are irrelevant now
            while not self._ev_queue.empty():
                (flushed_evt_type, flushed_evt_data) = self._ev_queue.get()
                if flush_keys:
                    '''
                    if flushed_evt_type == 'key' and flushed_evt_data == pbg.quit_key:
                        print("not flushed quit: ", flushed_evt_type, flushed_evt_data)
                        return None, flushed_evt_data, None
                    '''
                    print("Flushed: ", flushed_evt_type, flushed_evt_data)
                else:
                    if flushed_evt_type == 'key':
                        print("not flushed key: ", flushed_evt_type, flushed_evt_data)
                        return None, flushed_evt_data, None
                    print("Flushed: ", flushed_evt_type, flushed_evt_data)

            if self.ser_readline():
                if self.ser_writeline_crlf():
                    tx_data += s2b('\r\n')
                else:
                    tx_data += s2b('\n')

            bytes_written = self._fd_ser.write(tx_data)
            if bytes_written != len(tx_data):
                print("FIXME: x_ser written only ", bytes_written, " bytes")
            #print("x_ser written ", tx_data)

        try:
            # stop on blocking get()
            (evt_type, evt_data) = self._ev_queue.get(timeout=x_ser_timeout)
            # print("evt is ", evt_type, evt_data)
            if evt_type == 'key':
                print("x_ser key data is ", evt_data)
                key = evt_data

            elif evt_type == 'ser':
                #print("x_ser serial data is ", evt_data)
                rx_data = evt_data

            else:
                print("bug: unknown event")
                pass
        except queue.Empty:
            excp = queue.Empty
            return rx_data, key, excp
        '''
        except KeyboardInterrupt:
            excp = KeyboardInterrupt
            return rx_data, key, excp
        '''

        return rx_data, key, excp


