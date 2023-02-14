import threading

import time
import socket
from pathlib import Path

import binascii
import glob
import json
import requests
import inspect
import copy
import os

import pbglobals as pbg
from utils import *


JRN_DATA_PATH = '/home/pi/'
JRN_CFG_NAME = 'current.json'
JRN_UPLOAD_PREFIX = 'upload'
JRN_UPLOAD_PREFIX_DBG = 'dbg_upload'
JRN_REV_PREFIX = 'rev'
JRN_REV_PREFIX_DBG = 'dbg_rev'
JRN_UPLOAD_EXT = '.json'

URSULA_API_token = 'dcbe09a2b7d2c0dfe2b7d587288097ca2ad7c893ae69d9372dec62e83188a'
URSULA_URL = 'https://ursula-test.vendotek.eu//handler/urs/v0/msg'
ursula_headers = {
    'Content-type': 'application/json',
    'Authorization': 'Bearer {}'.format(URSULA_API_token),
    'Accept': '*/*'
}

URSULA_TID_CUG = ''

default_cfg = {
    'INVOICE': '100',
    'TXN_CURRENCY': 'CZK',
    'TX_SEQNO': '1000',
    'TERMINAL_SERNO': '',
    'TID_CUG':'',
}

ursula_req_template = {
    # request fields
    'TXN_TYPE': '',
    'TXN_TIMESTAMP': '',
    'TID_CUG':'',
    'TXN_AMOUNT': '',
    'TXN_CURRENCY': '',
    'ITEM': '',
    'USER_CREDENTIALS_VALUE': '',
    'USER_CREDENTIALS_TYPE': '',
    'INVOICE': '',
    'TID_BANKING': '',
    'TERMINAL_SERNO': '',
    'TX_SEQNO': '',
    'APPROVAL_CODE': '',
    'TXN_RECEIPT_PLAINTEXT': '',
    'TXN_APPROVED': '',
}

ursula_rsp_template = {
    # response fields
    'TXN_RESPONSE_CODE': '',
    'RRN': '',
    'HOST_TIMESTAMP': '',
    'HOST_TEXT': '',
    'CREDENTIALS_SCHEME_NAME': '',
    'TXN_AMOUNT': '',
    'TXN_AMOUNT_IS_BALANCE': '',
    'AUX_USER_CREDENTIALS_VALUE': '',
    'AUX_USER_CREDENTIALS_TYPE': '',
}


def sorter(item):
    l1 = item.split('/')
    l2 = l1[-1].split('.')
    l3 = l2[0].split(JRN_UPLOAD_PREFIX)
    # print("sorter ", item, l1, l2, l3)
    try:
        ret = int(l3[1])
    except:
        ret = 0
    return ret


def up_finder():
    for up_file in sorted(glob.glob(JRN_DATA_PATH + JRN_UPLOAD_PREFIX + '*' + JRN_UPLOAD_EXT), key=sorter):
        print("found upload file ", up_file)
        yield up_file


class UrsulaTxn:
    def __init__(self):
        self._config = copy.deepcopy(default_cfg)
        self._ursula_req = copy.deepcopy(ursula_req_template)
        self._ursula_rsp = copy.deepcopy(ursula_rsp_template)

        succ, self._config = self.get_config()
        if succ:
            print("found cfg file ")
            pass
        else:
            print("missing cfg file, saving default", logl='warning')
            self.save_default_config()
            succ, self._config = self.get_config()
            if succ:
                print("2nd: found cfg file ", logl='info')
                pass
            else:
                print("bug: STILL missing cfg file!", logl='error')

        self._txn_amt = ""
        self._inv = int(self._config['INVOICE'])
        self._timestamp = get_timestamp()

    @property
    def txn_amt(self):
        return self._txn_amt

    @txn_amt.setter
    def txn_amt(self, value):
        self._txn_amt = value
        self._ursula_req['TXN_AMOUNT'] = undot_amt(self._txn_amt)

    @property
    def txn_uc(self):
        return self._ursula_req['USER_CREDENTIALS_VALUE']

    @txn_uc.setter
    def txn_uc(self, value):
        self._ursula_req['USER_CREDENTIALS_VALUE'] = value
        self._ursula_req['USER_CREDENTIALS_TYPE'] = 'PAN'


    def get_config(self):
        for conf_file in glob.glob(JRN_DATA_PATH + JRN_CFG_NAME):
            print("found cfg file ", conf_file)
            with open(conf_file, 'r') as f:
                config = json.load(f)
                return True, config
        return False, None


    def save_default_config(self):
        if default_cfg['TERMINAL_SERNO'] == '':
            succ, pi_serial = get_pi_serial()
            if succ:
                default_cfg['TERMINAL_SERNO'] = pi_serial
                
        if default_cfg['TID_CUG'] == '':
            if URSULA_TID_CUG == '':
                default_cfg['TID_CUG'] = 'RPI' + default_cfg['TERMINAL_SERNO']
            else:
                default_cfg['TID_CUG'] = URSULA_TID_CUG

        with open(JRN_DATA_PATH + JRN_CFG_NAME, 'w') as f:
            json.dump(default_cfg, f)


    def save_new_config(self, new_cfg):
        if default_cfg['TERMINAL_SERNO'] == '':
            succ, pi_serial = get_pi_serial()
            if succ:
                default_cfg['TERMINAL_SERNO'] = pi_serial

        if default_cfg['TID_CUG'] == '':
            if URSULA_TID_CUG == '':
                default_cfg['TID_CUG'] = 'RPI' + default_cfg['TERMINAL_SERNO']
            else:
                default_cfg['TID_CUG'] = URSULA_TID_CUG

        with open(JRN_DATA_PATH + JRN_CFG_NAME, 'w') as f:
            print("next txn invoice will be ", new_cfg['INVOICE'])
            json.dump(new_cfg, f)


    def save_new_upload(self):
        upload_filename = JRN_DATA_PATH + JRN_UPLOAD_PREFIX + \
                          self._ursula_req['TX_SEQNO'] + JRN_UPLOAD_EXT
        with open(upload_filename, 'w') as f:
            json.dump(self._ursula_req, f)
            print("Saved ", upload_filename)

        # debug
        upload_filename = JRN_DATA_PATH + JRN_UPLOAD_PREFIX_DBG + \
                          self._ursula_req['TX_SEQNO'] + JRN_UPLOAD_EXT
        with open(upload_filename, 'w') as f:
            json.dump(self._ursula_req, f)
            print("Saved ", upload_filename)
            
        # invoice will increase regardless how valid is ursula rsp
        self._config['INVOICE'] = str(1 + int(self._config['INVOICE']))
        self._config['TX_SEQNO'] = str(1 + int(self._config['TX_SEQNO']))
        self.save_new_config(self._config)
            
     
    def save_reversal(self, new_reversal):
        upload_filename = JRN_DATA_PATH + JRN_REV_PREFIX + \
                          new_reversal['TX_SEQNO'] + JRN_UPLOAD_EXT
        with open(upload_filename, 'w') as f:
            json.dump(new_reversal, f)
            print("Saved ", upload_filename)

        # debug
        upload_filename = JRN_DATA_PATH + JRN_UPLOAD_PREFIX_DBG + \
                          new_upload['TX_SEQNO'] + JRN_UPLOAD_EXT
        with open(upload_filename, 'w') as f:
            json.dump(new_upload, f)
            print("Saved ", upload_filename)
     
    def generate_online_request(self, txn_type):
        # fill in self._ursula_req entries if txn is online

        # fill in template config field values
        for cfg_entry in self._config:
            self._ursula_req[cfg_entry] = self._config[cfg_entry]
            
        if txn_type == 'credit':
            self._ursula_req['TXN_TYPE'] = 'credit'
            # update timestamp
            self._timestamp = get_timestamp()
            self._ursula_req['TXN_TIMESTAMP'] = '20' + b2s(self._timestamp)
            #self._ursula_req['TXN_AMOUNT'] = undot_amt(self._txn_amt)
            # delete fields we don't need for this request
            del self._ursula_req['ITEM']
            del self._ursula_req['TID_BANKING']
            del self._ursula_req['APPROVAL_CODE']
            del self._ursula_req['TXN_RECEIPT_PLAINTEXT']
            del self._ursula_req['TXN_APPROVED']
            
            # todo TX_SEQNO can be enough
            #self.save_reversal(self._ursula_req)
        elif txn_type == 'sale':
            self._ursula_req['TXN_TYPE'] = 'sale'
            # update timestamp
            self._timestamp = get_timestamp()
            self._ursula_req['TXN_TIMESTAMP'] = '20' + b2s(self._timestamp)
            #self._ursula_req['TXN_AMOUNT'] = undot_amt(self._txn_amt)
            # delete fields we don't need for this request
            del self._ursula_req['ITEM']
            del self._ursula_req['TID_BANKING']
            del self._ursula_req['APPROVAL_CODE']
            del self._ursula_req['TXN_RECEIPT_PLAINTEXT']
            del self._ursula_req['TXN_APPROVED']
            
            # todo TX_SEQNO can be enough
            #self.save_reversal(self._ursula_req)
        else:
            print("no case for txn type", txn_type, logl='warning')

        print("txn request:")
        print(self._ursula_req)

    def generate_offline_request(self, txn_type):
        # fill in self._ursula_req entries if txn is offline

        # fill in template config field values
        for cfg_entry in self._config:
            self._ursula_req[cfg_entry] = self._config[cfg_entry]
            
        if txn_type == 'credit':
            self._ursula_req['TXN_TYPE'] = 'credit'
            # update timestamp
            self._timestamp = get_timestamp()
            self._ursula_req['TXN_TIMESTAMP'] = '20' + b2s(self._timestamp)
            #self._ursula_req['TXN_AMOUNT'] = undot_amt(self._txn_amt)
            # delete fields we don't need for this request
            del self._ursula_req['ITEM']
            del self._ursula_req['TID_BANKING']
            del self._ursula_req['TXN_RECEIPT_PLAINTEXT']

            #self._ursula_req['TXN_RESPONSE_CODE'] = '000'
            # todo make approval code secure deriving from keys from ping?
            self._ursula_req['APPROVAL_CODE'] = 'RND' + random_string_of_digits(5)
            self._ursula_req['TXN_APPROVED'] = 'Y'

            print("txn request:")
            print(self._ursula_req)
        else:
            print("no case for txn type", txn_type, logl='warning')


    def parse_response(self, ursula_rsp):
        print("ursula json response:")
        print(ursula_rsp)
        
        mandatory_fields = ['TXN_RESPONSE_CODE']
        for fld in mandatory_fields:
            if fld not in ursula_rsp:
                print("ursula response missing mandatory field", fld, logl='warning')
                return False
        
        for rsp_entry in ursula_rsp:
            self._ursula_rsp[rsp_entry] = ursula_rsp[rsp_entry]
        return True

    def transact(self):
        # send req to ursula and get rsp if we are lucky
        # fixme pre-send all advice msges as this will maintain correct order for 'TX_SEQNO'!
        payload = self._ursula_req
        r = requests.post(URSULA_URL, json=payload, headers=ursula_headers)
        print("status_code:")
        print(r.status_code)
        if r.status_code != 200:
            print("session cancelled (http rsp code)", logl='error')
            return False
        print("headers:")
        print(r.headers)
        print("content:")
        print(r.content)
        
        # invoice will increase regardless how valid is ursula rsp
        self._config['INVOICE'] = str(1 + int(self._config['INVOICE']))
        if not self.parse_response(r.json()):
            print("session cancelled (ursula rsp code)", logl='error')
            self.save_new_config(self._config)
            return False
        self._config['TX_SEQNO'] = str(1 + int(self._config['TX_SEQNO']))
        self.save_new_config(self._config)
        return True

    def is_txn_approved(self):
        if self._ursula_rsp['TXN_RESPONSE_CODE'] != '000':
            return False
        return True

    def get_card_balance(self):
        card_balance = ''
        if 'TXN_AMOUNT' in self._ursula_rsp:
            if 'TXN_AMOUNT_IS_BALANCE' in self._ursula_rsp:
                if self._ursula_rsp['TXN_AMOUNT_IS_BALANCE'] == 'Y':
                    card_balance = dot_amt(str(self._ursula_rsp['TXN_AMOUNT']))
                else:
                    print("ursula response TXN_AMOUNT_IS_BALANCE is not set for balance", \
                    self._ursula_rsp['TXN_AMOUNT_IS_BALANCE'], logl='warning')
            else:
                print("ursula response missing TXN_AMOUNT_IS_BALANCE field", logl='warning')
        else:
            print("ursula response missing TXN_AMOUNT field", logl='warning')

        return card_balance

    def get_host_text(self):
        host_text = ''
        if 'HOST_TEXT' in self._ursula_rsp:
            host_text = self._ursula_rsp['HOST_TEXT']
        else:
            print("ursula response missing HOST_TEXT field", logl='warning')

        return host_text


class TxnUploader:
    def __init__(self, ev_exit):
        self._ev_exit = ev_exit
        self._enabled = True
        self._ev_new_upload = threading.Event()

        self._T = threading.Thread(target=self.worker_thread, name='URSULA-Worker')
        self._T.start()
        print("TxnUploader instance inited ", threading.current_thread(), self._T)
        
        self.check_ursula_link()

    def __del__(self):
        print("TxnUploader instance deleted", threading.current_thread(), self._T)
        
        if inspect.currentframe().f_back is not None:
            print("called from ", inspect.currentframe().f_back.f_code.co_name)

        if threading.current_thread() == self._T:
            print("in worker_thread ==")
        elif self._T.is_alive():
            # self._T.join(10)
            self._T.join()
            print("worker_thread joined")
        else:
            print("worker_thread dead")

    def new_upload(self):
        # speed up uploader: cancel normal 5 min wait
        # wait for 5 seconds
        # upload whatever is pending
        self._ev_new_upload.set()

    def upload_success(self, ursula_rsp):
        print("ursula json response:")
        print(ursula_rsp)
        if ursula_rsp['TXN_RESPONSE_CODE'] != '000':
            print("ursula response code not ok: ", ursula_rsp['TXN_RESPONSE_CODE'], logl='warning')
            return False
        return True

    def uploads_pending(self):
        # todo mutex this
        for up_entry in up_finder():
            return True
        return False
            
    def upload_session(self):
        for up_entry in up_finder():
            print("processing upload file ", up_entry)

            with open(up_entry, 'r') as f:
                payload = json.load(f)

                print("file contents: ", payload)
                r = requests.post(URSULA_URL, json=payload, headers=ursula_headers)
                print("status_code:")
                print(r.status_code)
                if r.status_code != 200:
                    print("session cancelled (http rsp code)", logl='error')
                    self.check_ursula_link()
                    return
                print("headers:")
                print(r.headers)
                print("content:")
                print(r.content)
                if not self.upload_success(r.json()):
                    print("session cancelled (ursula rsp code)", logl='error')
                    return
                else:
                    print("good sess, deleting upload file ", up_entry)
                    os.remove(up_entry)
                    pbg.ursula_link_up = True

    def check_ursula_link(self):
        print("Sending HTTP Options to ursula ")
        try:
            r = requests.options(url=URSULA_URL)
            print("status_code:")
            print(r.status_code)
            # assume any 2xx http response is good here
            if 200 <= r.status_code <= 299:
                pbg.ursula_link_up = True
            else:
                print("http options failed", logl='warning')
                pbg.ursula_link_up = False
        #except (ConnectionError, ConnectionRefusedError):
        except Exception as e_ul:
            print("Exception from requests ", e_ul, logl='error')
            print('type is:', e_ul.__class__.__name__)
            
            print("connection refused", logl='warning')
            pbg.ursula_link_up = False

    def worker_thread(self):
        print("worker_thread started")

        time_iter = 0

        while self._enabled:
            while time_iter < 60:
                if self._ev_exit.is_set():
                    self._enabled = False
                    print("worker_thread got shutdown evt")
                    return

                if self._ev_new_upload.wait(5.0):
                    # got the event
                    self._ev_new_upload.clear()

                    time.sleep(5.0)
                    self.upload_session()
                    time_iter = 0
                    continue
                else:
                    # timed out
                    time_iter += 1
                    
            if not pbg.ursula_link_up:
                self.check_ursula_link()

            self.upload_session()
            time_iter = 0

        print("worker_thread terminating...")

