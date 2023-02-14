#! /usr/bin/env python3

from logprint import print

import fcntl
import os
import queue
import select
import sys
import termios
import threading
import _thread

import time
import serial
import socket
import configparser
from datetime import datetime
from enum import *
from pathlib import Path

import binascii
import glob
import json
import requests
import logging
import logging.handlers
import inspect

import builtins as __builtin__
from traceback import print_exc
import argparse
import io
import platform

import pbglobals as pbg
from pbce import CustomException
from pbconfig import PBConfig

import hopper
import bnv
import carddispenser
import vteknfc
import ursula


def exception_logger(args):
    print(f'caught {args.exc_type} with value {args.exc_value} in thread {args.thread}\n')
    pbg.logger.error("Uncaught exception", exc_info=(args.exc_type, args.exc_value, args.exc_traceback))
    _thread.interrupt_main()


threading.excepthook = exception_logger

'''
class CustomException(Exception):
    def __init__(self, message):
        super().__init__()
        self.message = message
'''

class ProgFlow(Enum):
    INIT = auto()
    PB_IDLE = auto()
    PB_COINS_FOR_NOTES = auto()
    PB_COINS_FOR_NOTES_ACCEPT_NOTES_START = auto()
    PB_COINS_FOR_NOTES_ACCEPT_NOTES_STOP = auto()
    PB_CARD_FOR_NOTES = auto()
    PB_CARD_FOR_NOTES_ACCEPT_NOTES_START = auto()
    PB_CARD_FOR_NOTES_ACCEPT_NOTES_STOP = auto()
    PB_CARD_FOR_NOTES_DISPENSE_AND_READ_CARD = auto()
    PB_TOPUP_FOR_NOTES_READ_CARD = auto()
    PB_CARD_BALANCE_READ_CARD = auto()
    FINISH = auto()
    REPEAT = auto()
    NEXT = auto()


progflow = [
    {
        'state': ProgFlow.INIT,
        'proc': 'pb_init',
    },
    {
        'state': ProgFlow.PB_IDLE,
        'proc': 'pb_idle',
    },
    {
        'state': ProgFlow.PB_COINS_FOR_NOTES,
        'proc': 'pb_coins_for_notes',
    },
    {
        'state': ProgFlow.PB_COINS_FOR_NOTES_ACCEPT_NOTES_START,
        'proc': 'pb_coins_for_notes_accept_notes_start',
    },
    {
        'state': ProgFlow.PB_COINS_FOR_NOTES_ACCEPT_NOTES_STOP,
        'proc': 'pb_coins_for_notes_accept_notes_stop',
    },
    {
        'state': ProgFlow.PB_CARD_FOR_NOTES,
        'proc': 'pb_card_for_notes',
    },
    {
        'state': ProgFlow.PB_CARD_FOR_NOTES_ACCEPT_NOTES_START,
        'proc': 'pb_card_for_notes_accept_notes_start',
    },
    {
        'state': ProgFlow.PB_CARD_FOR_NOTES_ACCEPT_NOTES_STOP,
        'proc': 'pb_card_for_notes_accept_notes_stop',
    },
    {
        'state': ProgFlow.PB_CARD_FOR_NOTES_DISPENSE_AND_READ_CARD,
        'proc': 'pb_card_for_notes_dispense_and_read_card',
    },
    {
        'state': ProgFlow.PB_TOPUP_FOR_NOTES_READ_CARD,
        'proc': 'pb_topup_for_notes_read_card',
    },
    {
        'state': ProgFlow.PB_CARD_BALANCE_READ_CARD,
        'proc': 'pb_card_balance_read_card',
    },
    {
        'state': ProgFlow.FINISH,
        'proc': 'wrapup',
    },
]


class ProgStages:
    def __init__(self, gui2sm_queue, sm2gui_queue, ev_exit_):
        self._gui2sm_queue = gui2sm_queue
        self._sm2gui_queue = sm2gui_queue
        self._ev_exit = ev_exit_

        self._ui_cmd = None

    def pb_init(self):
        print("Entered pb_init..")
        return ProgFlow.NEXT

    def pb_idle(self):
        print("Entered pb_idle..")
        while True:
            try:
                self._ui_cmd = self._gui2sm_queue.get(timeout=0.2)
                print("User cmd", self._ui_cmd)
                break
            except queue.Empty:
                if self._ev_exit.is_set():
                    return ProgFlow.FINISH
        
        if self._ui_cmd['command'] == 'coins_for_notes':
            return ProgFlow.PB_COINS_FOR_NOTES
        elif self._ui_cmd['command'] == 'coins_for_notes_accept_notes_start':
            return ProgFlow.PB_COINS_FOR_NOTES_ACCEPT_NOTES_START
        elif self._ui_cmd['command'] == 'coins_for_notes_accept_notes_stop':
            return ProgFlow.PB_COINS_FOR_NOTES_ACCEPT_NOTES_STOP
        elif self._ui_cmd['command'] == 'card_for_notes':
            return ProgFlow.PB_CARD_FOR_NOTES
        elif self._ui_cmd['command'] == 'card_for_notes_accept_notes_start':
            return ProgFlow.PB_CARD_FOR_NOTES_ACCEPT_NOTES_START
        elif self._ui_cmd['command'] == 'card_for_notes_accept_notes_stop':
            return ProgFlow.PB_CARD_FOR_NOTES_ACCEPT_NOTES_STOP
        elif self._ui_cmd['command'] == 'card_for_notes_dispense_and_read_card':
            return ProgFlow.PB_CARD_FOR_NOTES_DISPENSE_AND_READ_CARD
        elif self._ui_cmd['command'] == 'topup_for_notes_read_card':
            return ProgFlow.PB_TOPUP_FOR_NOTES_READ_CARD
        elif self._ui_cmd['command'] == 'card_balance_read_card':
            return ProgFlow.PB_CARD_BALANCE_READ_CARD
            
        else:
            print("no handler for user cmd", self._ui_cmd, logl='warning')

        return ProgFlow.REPEAT
        #return ProgFlow.FINISH

    def pb_coins_for_notes_accept_notes_start(self):
        print("Entered pb_coins_for_notes_accept_notes_start..")
        '''
        # test nfc
        nfc_retval = pbg.nfcInstance.readCard(timeout=24.0)
        print("readCard finished with", nfc_retval)
        pbg.nfcInstance.removeCard()
        print("removeCard finished")
        '''
        '''
        # test ursula
        print("ursula TEST")
        ursula_txn = ursula.UrsulaTxn()
        
        ursula_txn.txn_amt = str(70000)
        ursula_txn.txn_uc = '9203111122223333'
        
        ursula_txn.generate_offline_request('credit')

        ursula_txn.save_new_upload()
        
        # kick the ursula uploader
        pbg.ursulaInstance.new_upload()  
        print("ursula kicked")
        '''
        
        bnv_cmd = bnv.get_bnv_cmd_template('accept_notes_start')
        pbg.bnvInstance.bnv_cmd_q.put(bnv_cmd)

        while True:
            if self._ev_exit.is_set():
                return ProgFlow.FINISH

            if not pbg.bnvInstance.bnv_cmd_rsp_q.empty():
                bnv_cmd_rsp = pbg.bnvInstance.bnv_cmd_rsp_q.get()
                print('BNV cmd response', bnv_cmd_rsp)
                if bnv_cmd_rsp['command'] == 'accept_notes_start':
                    if bnv_cmd_rsp['status'] == 'complete':
                        self._ui_cmd['status'] = bnv_cmd_rsp['status']
                        self._ui_cmd['result'] = bnv_cmd_rsp['result']
                        self._ui_cmd['customer_balance'] = bnv_cmd_rsp['amount']
                        self._ui_cmd['message_bnv'] = bnv_cmd_rsp['message']
                        self._sm2gui_queue.put(self._ui_cmd)
                        break
                    else:
                        # send an update to customer balance
                        self._ui_cmd['result'] = bnv_cmd_rsp['result']
                        self._ui_cmd['status'] = bnv_cmd_rsp['status']
                        self._ui_cmd['customer_balance'] = bnv_cmd_rsp['amount']
                        self._ui_cmd['message_bnv'] = bnv_cmd_rsp['message']
                        self._sm2gui_queue.put(self._ui_cmd)

            if not self._gui2sm_queue.empty():
                self._ui_cmd = self._gui2sm_queue.get()
                print("Another user cmd", self._ui_cmd)
                
                if self._ui_cmd['command'] == 'coins_for_notes_accept_notes_start':
                    # ignore
                    print("already executing", self._ui_cmd['command'])
                elif self._ui_cmd['command'] == 'coins_for_notes_accept_notes_stop':
                    # 'next' or 'cancel'
                    # todo
                    return ProgFlow.PB_COINS_FOR_NOTES_ACCEPT_NOTES_STOP
                else:
                    print("no handler for user cmd", self._ui_cmd, logl='warning')

            time.sleep(0.2)


        return ProgFlow.PB_IDLE

    def pb_coins_for_notes_accept_notes_stop(self):
        print("Entered pb_coins_for_notes_accept_notes_stop..")
        bnv_cmd = bnv.get_bnv_cmd_template('accept_notes_stop')
        pbg.bnvInstance.bnv_cmd_q.put(bnv_cmd)

        while True:
            if self._ev_exit.is_set():
                return ProgFlow.FINISH

            if not pbg.bnvInstance.bnv_cmd_rsp_q.empty():
                bnv_cmd_rsp = pbg.bnvInstance.bnv_cmd_rsp_q.get()
                print('BNV cmd response', bnv_cmd_rsp)
                if bnv_cmd_rsp['command'] == 'accept_notes_stop':
                    if bnv_cmd_rsp['status'] == 'complete':
                        self._ui_cmd['status'] = bnv_cmd_rsp['status']
                        self._ui_cmd['result'] = bnv_cmd_rsp['result']
                        self._ui_cmd['customer_balance'] = bnv_cmd_rsp['amount']
                        self._ui_cmd['message_bnv'] = bnv_cmd_rsp['message']
                        self._sm2gui_queue.put(self._ui_cmd)
                        break
                    else:
                        # send an update to customer balance
                        # we shouldn't be here
                        self._ui_cmd['status'] = bnv_cmd_rsp['status']
                        self._ui_cmd['result'] = bnv_cmd_rsp['result']
                        self._ui_cmd['customer_balance'] = bnv_cmd_rsp['amount']
                        self._ui_cmd['message_bnv'] = bnv_cmd_rsp['message']
                        self._sm2gui_queue.put(self._ui_cmd)

            time.sleep(0.2)

        return ProgFlow.PB_IDLE

    def pb_coins_for_notes(self):
        print("Entered pb_coins_for_notes..")
        #time.sleep(2)
        self._ui_cmd['result'] = 'unavailable'
        self._ui_cmd['status'] = 'executing'
        self._ui_cmd['message_hopper'] = 'Hopper is hopping!'
        self._ui_cmd['message_bnv'] = 'BNV is bnving!'
        self._sm2gui_queue.put(self._ui_cmd)
        
        hopper_cmd = hopper.get_hopper_cmd_template('payout_amount')
        hopper_cmd['amount'] = self._ui_cmd['coins']
        pbg.hopperInstance.hopper_cmd_q.put(hopper_cmd)
        
        bnv_cmd = bnv.get_bnv_cmd_template('dispense_notes')
        bnv_cmd['amount'] = self._ui_cmd['notes']
        pbg.bnvInstance.bnv_cmd_q.put(bnv_cmd)
        
        #bnv_cmd_rsp = None
        #hopper_cmd_rsp = None

        hopper_done = False
        bnv_done = False
        
        while True:
            #if hopper_cmd_rsp is None:
            if not pbg.hopperInstance.hopper_cmd_rsp_q.empty():
                hopper_cmd_rsp = pbg.hopperInstance.hopper_cmd_rsp_q.get()
                print('Hopper cmd response', hopper_cmd_rsp)
                if hopper_cmd_rsp['status'] == 'complete':
                    hopper_done = True
            
            #if bnv_cmd_rsp is None:
            if not pbg.bnvInstance.bnv_cmd_rsp_q.empty():
                bnv_cmd_rsp = pbg.bnvInstance.bnv_cmd_rsp_q.get()
                print('BNV cmd response', bnv_cmd_rsp)
                if bnv_cmd_rsp['status'] == 'complete':
                    bnv_done = True
                    
                if bnv_cmd_rsp['result'] == 'popup_show':
                    self._ui_cmd['message_bnv'] = bnv_cmd_rsp['message']
                    self._ui_cmd['result'] = bnv_cmd_rsp['result']
                    self._ui_cmd['status'] = 'executing'
                    self._sm2gui_queue.put(self._ui_cmd)
                elif bnv_cmd_rsp['result'] == 'popup_hide':
                    self._ui_cmd['message_bnv'] = bnv_cmd_rsp['message']
                    self._ui_cmd['result'] = bnv_cmd_rsp['result']
                    self._ui_cmd['status'] = 'executing'
                    self._sm2gui_queue.put(self._ui_cmd)
                        
            if hopper_done and bnv_done:
                break
                
            time.sleep(0.2)
        
        if hopper_cmd_rsp['result'] == 'success':
            if hopper_cmd_rsp['message'] != '':
                self._ui_cmd['message_hopper'] = hopper_cmd_rsp['message']
            else:
                self._ui_cmd['message_hopper'] = 'PLEASE COLLECT YOUR COINS'
        else:
            if hopper_cmd_rsp['message'] != '':
                self._ui_cmd['message_hopper'] = hopper_cmd_rsp['message']
            else:
                self._ui_cmd['message_hopper'] = 'SORRY THERE WAS A FAULT (H)'
                
        if bnv_cmd_rsp['result'] == 'success':
            if bnv_cmd_rsp['message'] != '':
                self._ui_cmd['message_bnv'] = bnv_cmd_rsp['message']
            else:
                self._ui_cmd['message_bnv'] = 'YOU COLLECTED ALL BANKNOTES'
        else:
            if bnv_cmd_rsp['message'] != '':
                self._ui_cmd['message_bnv'] = bnv_cmd_rsp['message']
            else:
                self._ui_cmd['message_bnv'] = 'SORRY THERE WAS A FAULT (B)'

        self._ui_cmd['result'] = 'unavailable'
        self._ui_cmd['status'] = 'executing'
        self._sm2gui_queue.put(self._ui_cmd)
        time.sleep(5)
        
        if hopper_cmd_rsp['result'] == 'success' and bnv_cmd_rsp['result'] == 'success':
            self._ui_cmd['result'] = 'success'
            self._ui_cmd['qr'] = 'www.mobivend.eu/receipt'
        else:
            self._ui_cmd['result'] = 'failure'
            self._ui_cmd['qr'] = 'www.mobivend.eu/recovery'
            
        self._ui_cmd['status'] = 'complete'
        self._sm2gui_queue.put(self._ui_cmd)
        
        return ProgFlow.PB_IDLE


    def pb_card_for_notes_accept_notes_start(self):
        print("Entered pb_card_for_notes_accept_notes_start..")
        bnv_cmd = bnv.get_bnv_cmd_template('accept_notes_start')
        # no notes back are given in this txn!
        bnv_cmd['check_dispense_values'] = False
        pbg.bnvInstance.bnv_cmd_q.put(bnv_cmd)

        while True:
            if self._ev_exit.is_set():
                return ProgFlow.FINISH

            if not pbg.bnvInstance.bnv_cmd_rsp_q.empty():
                bnv_cmd_rsp = pbg.bnvInstance.bnv_cmd_rsp_q.get()
                print('BNV cmd response', bnv_cmd_rsp)
                if bnv_cmd_rsp['command'] == 'accept_notes_start':
                    if bnv_cmd_rsp['status'] == 'complete':
                        self._ui_cmd['status'] = bnv_cmd_rsp['status']
                        self._ui_cmd['result'] = bnv_cmd_rsp['result']
                        self._ui_cmd['customer_balance'] = bnv_cmd_rsp['amount']
                        self._ui_cmd['message_bnv'] = bnv_cmd_rsp['message']
                        self._sm2gui_queue.put(self._ui_cmd)
                        break
                    else:
                        # send an update to customer balance
                        self._ui_cmd['result'] = bnv_cmd_rsp['result']
                        self._ui_cmd['status'] = bnv_cmd_rsp['status']
                        self._ui_cmd['customer_balance'] = bnv_cmd_rsp['amount']
                        self._ui_cmd['message_bnv'] = bnv_cmd_rsp['message']
                        self._sm2gui_queue.put(self._ui_cmd)

            if not self._gui2sm_queue.empty():
                self._ui_cmd = self._gui2sm_queue.get()
                print("Another user cmd", self._ui_cmd)
                
                if self._ui_cmd['command'] == 'card_for_notes_accept_notes_start':
                    # ignore
                    print("already executing", self._ui_cmd['command'])
                elif self._ui_cmd['command'] == 'card_for_notes_accept_notes_stop':
                    # 'next' or 'cancel'
                    # todo
                    return ProgFlow.PB_CARD_FOR_NOTES_ACCEPT_NOTES_STOP
                else:
                    print("no handler for user cmd", self._ui_cmd, logl='warning')

            time.sleep(0.2)

        return ProgFlow.PB_IDLE

    def pb_card_for_notes_accept_notes_stop(self):
        print("Entered pb_card_for_notes_accept_notes_stop..")
        bnv_cmd = bnv.get_bnv_cmd_template('accept_notes_stop')
        pbg.bnvInstance.bnv_cmd_q.put(bnv_cmd)

        while True:
            if self._ev_exit.is_set():
                return ProgFlow.FINISH

            if not pbg.bnvInstance.bnv_cmd_rsp_q.empty():
                bnv_cmd_rsp = pbg.bnvInstance.bnv_cmd_rsp_q.get()
                print('BNV cmd response', bnv_cmd_rsp)
                if bnv_cmd_rsp['command'] == 'accept_notes_stop':
                    if bnv_cmd_rsp['status'] == 'complete':
                        self._ui_cmd['status'] = bnv_cmd_rsp['status']
                        self._ui_cmd['result'] = bnv_cmd_rsp['result']
                        self._ui_cmd['customer_balance'] = bnv_cmd_rsp['amount']
                        self._ui_cmd['message_bnv'] = bnv_cmd_rsp['message']
                        self._sm2gui_queue.put(self._ui_cmd)
                        break
                    else:
                        # send an update to customer balance
                        # we shouldn't be here
                        self._ui_cmd['status'] = bnv_cmd_rsp['status']
                        self._ui_cmd['result'] = bnv_cmd_rsp['result']
                        self._ui_cmd['customer_balance'] = bnv_cmd_rsp['amount']
                        self._ui_cmd['message_bnv'] = bnv_cmd_rsp['message']
                        self._sm2gui_queue.put(self._ui_cmd)

            time.sleep(0.2)

        return ProgFlow.PB_IDLE

    def pb_card_for_notes(self):
        print("Entered pb_card_for_notes..")

        # compile credit advice for ursula and get out
        post_status = True
        ursula_txn = ursula.UrsulaTxn()
        
        ursula_txn.txn_amt = str(self._ui_cmd['notes'])
        ursula_txn.txn_uc = self._ui_cmd['credentials_value']
        
        ursula_txn.generate_offline_request('credit')

        ursula_txn.save_new_upload()
        
        # kick the ursula uploader
        pbg.ursulaInstance.new_upload()  
        print("ursula kicked")
        
        if post_status:
            self._ui_cmd['result'] = 'success'
            self._ui_cmd['qr'] = 'www.mobivend.eu/receipt'
        else:
            self._ui_cmd['result'] = 'failure'
            self._ui_cmd['qr'] = 'www.mobivend.eu/recovery'
        self._ui_cmd['status'] = 'complete'
        self._sm2gui_queue.put(self._ui_cmd)
        
        return ProgFlow.PB_IDLE


    def pb_card_for_notes_dispense_and_read_card(self):
        print("Entered pb_card_for_notes_dispense_and_read_card..")
        #self._ui_cmd['result'] = 'unavailable'
        self._ui_cmd['result'] = 'popup_show'
        self._ui_cmd['status'] = 'executing'
        self._ui_cmd['message_cd'] = 'Dispensing card...'
        self._ui_cmd['message_nfc'] = ''
        self._sm2gui_queue.put(self._ui_cmd)
        
        cd_result = carddispenser.dispense_card(timeout=3.5)
        if cd_result:
            self._ui_cmd['message_cd'] = 'PLEASE COLLECT YOUR CARD AND\nPROCEED TO ACTIVATE'
        else:
            self._ui_cmd['message_cd'] = 'SORRY THERE WAS A FAULT (CD)'

        #self._ui_cmd['result'] = 'unavailable'
        self._ui_cmd['result'] = 'popup_show'
        self._ui_cmd['status'] = 'executing'
        self._sm2gui_queue.put(self._ui_cmd)
        time.sleep(5)
        
        self._ui_cmd['result'] = 'popup_hide'
        self._ui_cmd['status'] = 'executing'
        self._sm2gui_queue.put(self._ui_cmd)
        
        time.sleep(0.2)
        if not cd_result:
            self._ui_cmd['result'] = 'failure'
            self._ui_cmd['qr'] = 'www.mobivend.eu/recovery'
            self._ui_cmd['status'] = 'complete'
            self._sm2gui_queue.put(self._ui_cmd)
        else:
            nfc_retval = pbg.nfcInstance.readCard(timeout=24.0)
            print("readCard finished with", nfc_retval)
            succ, pan, uid = nfc_retval
            pbg.nfcInstance.removeCard()
            print("removeCard finished")
            
            if succ:
                self._ui_cmd['result'] = 'success'
                self._ui_cmd['qr'] = 'www.mobivend.eu/pre-receipt'
                self._ui_cmd['status'] = 'complete'
                self._ui_cmd['credentials_value'] = pan
                self._sm2gui_queue.put(self._ui_cmd)
            else:
                self._ui_cmd['result'] = 'failure'
                self._ui_cmd['qr'] = 'www.mobivend.eu/recovery'
                self._ui_cmd['status'] = 'complete'
                self._sm2gui_queue.put(self._ui_cmd)
        
        return ProgFlow.PB_IDLE

    def pb_topup_for_notes_read_card(self):
        print("Entered pb_topup_for_notes_read_card..")
        
        nfc_retval = pbg.nfcInstance.readCard(timeout=24.0)
        print("readCard finished with", nfc_retval)
        succ, pan, uid = nfc_retval
        pbg.nfcInstance.removeCard()
        print("removeCard finished")
        
        if succ:
            self._ui_cmd['result'] = 'success'
            self._ui_cmd['qr'] = 'www.mobivend.eu/pre-receipt'
            self._ui_cmd['status'] = 'complete'
            self._ui_cmd['credentials_value'] = pan
            self._sm2gui_queue.put(self._ui_cmd)
        else:
            self._ui_cmd['result'] = 'failure'
            self._ui_cmd['qr'] = 'www.mobivend.eu/recovery'
            self._ui_cmd['status'] = 'complete'
            self._sm2gui_queue.put(self._ui_cmd)
        
        return ProgFlow.PB_IDLE

    def pb_card_balance_read_card(self):
        print("Entered pb_card_balance_read_card..")
        
        nfc_retval = pbg.nfcInstance.readCard(timeout=24.0)
        print("readCard finished with", nfc_retval)
        succ, pan, uid = nfc_retval
        pbg.nfcInstance.removeCard()
        print("removeCard finished")
        
        if succ:
            succ = False
            is_uploads_pending = pbg.ursulaInstance.uploads_pending()
            if pbg.ursula_link_up and not is_uploads_pending:
                ursula_txn = ursula.UrsulaTxn()
                ursula_txn.txn_amt = str("0")
                ursula_txn.txn_uc = pan
                ursula_txn.generate_online_request('sale')
                if ursula_txn.transact():
                    if ursula_txn.is_txn_approved():
                        card_balance = ursula_txn.get_card_balance()
                        if card_balance != '':
                            self._ui_cmd['message_ursula'] = 'YOUR ACCOUNT BALANCE\nIS ' + \
                            card_balance + ' ' + pbg.currency
                            succ = True
                    else:
                        print("card_balance declined")
                        host_text = ursula_txn.get_host_text()
                        if host_text != '':
                            self._ui_cmd['message_ursula'] = 'TRANSACTION FAILED\n' + \
                            host_text
            else:
                print("card_balance failed", pbg.ursula_link_up, is_uploads_pending)
                self._ui_cmd['message_ursula'] = 'TRANSACTION FAILED\n' + \
                'TRY AGAIN LATER'
                
            self._ui_cmd['result'] = 'popup_show'
            self._ui_cmd['status'] = 'executing'
            self._sm2gui_queue.put(self._ui_cmd)
            time.sleep(5)
            
            self._ui_cmd['result'] = 'popup_hide'
            self._ui_cmd['status'] = 'executing'
            self._sm2gui_queue.put(self._ui_cmd)
            
            time.sleep(0.2)
            if succ:
                self._ui_cmd['result'] = 'success'
                self._ui_cmd['status'] = 'complete'
                self._sm2gui_queue.put(self._ui_cmd)
            else:
                self._ui_cmd['result'] = 'failure'
                self._ui_cmd['status'] = 'complete'
                self._sm2gui_queue.put(self._ui_cmd)
        else:
            self._ui_cmd['result'] = 'failure'
            self._ui_cmd['status'] = 'complete'
            self._sm2gui_queue.put(self._ui_cmd)
        
        return ProgFlow.PB_IDLE

    def wrapup(self):
        # dummy never called
        return ProgFlow.FINISH


def coreSM(gui2sm_queue, sm2gui_queue, ev_shutdown):
    print("Entered coreSM..")
    progstages = ProgStages(gui2sm_queue, sm2gui_queue, ev_shutdown)

    pfstage = ProgFlow.INIT
    pfstage_i = 0

    while pfstage != ProgFlow.FINISH:
        # for fstage in progflow:
        flow_entry = progflow[pfstage_i]

        method = getattr(progstages, flow_entry['proc'])
        next_pfstage = method()
        # print("to be next...", next_pfstage)

        if next_pfstage == ProgFlow.FINISH:
            break
        elif next_pfstage == ProgFlow.REPEAT:
            # pfstage unchanged
            # print(" Repeating...")
            continue
        elif next_pfstage == ProgFlow.NEXT:
            pfstage_i += 1
            flow_entry = progflow[pfstage_i]
            pfstage = flow_entry['state']
            # print(" next...", pfstage)
        else:
            matches = [x for x in progflow if x['state'] == next_pfstage]
            matches_i = progflow.index(matches[0])
            # print('matches ', matches)
            # print('matches_i ', matches_i)
            if len(matches) > 0:
                next_flowentry = matches[0]
                pfstage = next_flowentry['state']
                pfstage_i = matches_i
                # print(" custom...", pfstage)
            else:
                print(" bug - no matches...", next_pfstage, logl='critical')
                raise CustomException('critical bug, application stopped')
    print("Exiting coreSM..")


def coreStart():
    cur_dir = os.getcwd()

    log_format = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
    syslog_format = logging.Formatter("[%(levelname)s] %(message)s")
    #console_log_format = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%b-%d %H:%M")
    console_log_format = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)s] %(message)s", datefmt="%b-%d %H:%M")

    pbg.logger = logging.getLogger()
    pbg.logger.setLevel(logging.DEBUG)

    console_logger = logging.StreamHandler(sys.stdout)
    console_logger.setFormatter(console_log_format)
    pbg.logger.addHandler(console_logger)

    syslog_logger = logging.handlers.SysLogHandler(address='/dev/log', facility=19)
    syslog_logger.setFormatter(syslog_format)
    pbg.logger.addHandler(syslog_logger)

    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True
    requests_log.addHandler(console_logger)
    requests_log.addHandler(syslog_logger)

    print("PayBox v%s" % pbg.app_version, logl='info')

    parser = argparse.ArgumentParser()
    parser.add_argument("--inifile", help="init from .ini file at this location")
    args = parser.parse_args()

    print("Using Runtime Python Version %s" % platform.python_version(), logl='info')
    print("Launched from ", cur_dir, logl='info')

    if args.inifile:
        print("init from ", args.inifile, logl='info')
        pbg.ini_file_name = args.inifile
    else:
        pbg.ini_file_name = cur_dir + '/' + pbg.ini_file_name_default

    pbg.pbConfig = PBConfig(pbg.ini_file_name)
    pbg.pbConfig.readConfig()

    pbg.ev_shutdown = threading.Event()

    pbg.gui2sm_queue = queue.Queue()
    pbg.sm2gui_queue = queue.Queue()

    pbg.coreSMT = threading.Thread(target=coreSM, args=(pbg.gui2sm_queue, pbg.sm2gui_queue, pbg.ev_shutdown), name='Core-SMT')
    pbg.coreSMT.start()

def hopperStart():
    pbg.hopperInstance = hopper.SmartHopper(serial=pbg.pbConfig.gHOPPER_SERIAL_DEVICE)

def hopperStop():
    del pbg.hopperInstance

def bnvStart():
    pbg.bnvInstance = bnv.JcmBnv(serial=pbg.pbConfig.gBNV_SERIAL_DEVICE)

def bnvStop():
    del pbg.bnvInstance

def nfcStart():
    pbg.nfcInstance = vteknfc.VtekNfc(serial=pbg.pbConfig.gNFC_SERIAL_DEVICE)

def nfcStop():
    del pbg.nfcInstance

def ursulaStart():
    pbg.ursulaInstance = ursula.TxnUploader(pbg.ev_shutdown)

def ursulaStop():
    del pbg.ursulaInstance


def coreShutdown():
    if pbg.ev_shutdown is not None:
        pbg.ev_shutdown.set()

    ursulaStop()
    nfcStop()
    hopperStop()
    bnvStop()

    if pbg.coreSMT is not None:
        pbg.coreSMT.join()
    print("coreSMT joined...")


def coreMain():
    coreStart()
    ursulaStart()
    nfcStart()
    hopperStart()
    bnvStart()
