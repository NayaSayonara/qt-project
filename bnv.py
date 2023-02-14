from logprint import print

import time
import struct
import queue
import serial
import threading
import inspect
import sys
import copy

import pbglobals as pbg
from utils import *
from cc2 import *
from eventdetect import EventDetect
from cc2helper import Cc2Helper
from trackedobject import TrackedObject
from bitmask import BitMask
from billstatus import BillStatus


bnv_commands = \
[
{
    # request
    'command': 'dispense_notes',
    'amount': 0,
    # response
    'result': 'unknown',
    'status': 'unknown',
    'message': '',
},
{
    # request
    'command': 'accept_notes_start',
    'check_dispense_values': True,
    'session_timeout': 0,
    # response
    'result': 'unknown',
    'status': 'unknown',
    'message': '',
    'amount': 0,
},
{
    # request
    'command': 'accept_notes_stop',
    # response
    'result': 'unknown',
    'status': 'unknown',
    'message': '',
    'amount': 0,
},
]

def get_bnv_cmd_template(cmd):
    for i in range(len(bnv_commands)):
        bnv_command = bnv_commands[i]
        if bnv_command['command'] == cmd:
            return copy.deepcopy(bnv_command)


class JcmBnv:
    '''
    'val' denomination actual value in cents
    'lvl': level of notes in the recycler
    'cur': currency of denomination 2 chars
    'rut': RFU
    'qty': quantity to be dispensed for dispense cmd
    'bill': bill id assigned for this denomination
    'inht': inhibit status for this denomination
    'rcvd': number of notes deposited by customer in a session
    '''
    _denoms_template = \
    [
    {
        'val': 10000,
        'lvl': 0,
        'cur': 'xxx',
        'rut': -1,
        'qty': 0,
        'bill': 0,
        'inht': 0,
        'rcvd': 0,
    },
    {
        'val': 20000,
        'lvl': 0,
        'cur': 'xxx',
        'rut': -1,
        'qty': 0,
        'bill': 0,
        'inht': 0,
        'rcvd': 0,
    },
    {
        'val': 50000,
        'lvl': 0,
        'cur': 'xxx',
        'rut': -1,
        'qty': 0,
        'bill': 0,
        'inht': 0,
        'rcvd': 0,
    },
    {
        'val': 100000,
        'lvl': 0,
        'cur': 'xxx',
        'rut': -1,
        'qty': 0,
        'bill': 0,
        'inht': 0,
        'rcvd': 0,
    },
    {
        'val': 200000,
        'lvl': 0,
        'cur': 'xxx',
        'rut': -1,
        'qty': 0,
        'bill': 0,
        'inht': 0,
        'rcvd': 0,
    },
    {
        'val': 500000,
        'lvl': 0,
        'cur': 'xxx',
        'rut': -1,
        'qty': 0,
        'bill': 0,
        'inht': 0,
        'rcvd': 0,
    },
    ]
    
    def __init__(self, country='CZ', serial="/dev/ttyUSB1"):
        self.ev_detect = None
        self.country = country
        self.serial_dev = serial
        self.fd_ser = None
        self.EDT = None
        self.BPT = None
        self.ev_q = queue.Queue()
        self.initialised = False
        # global 'working' flag for BNV
        # misconfiguration, no/bad replies etc - all goes here
        # todo this flag is never reset back to False!
        self.malfunctioned = False
        
        self.bnv_cmd_q = queue.Queue()
        self.bnv_cmd_rsp_q = queue.Queue()
        self.bnv_cmd_current = None
        
        self.min_delay_time = 0
        self.poll_delay_time = 0
        self.cc2Helper = None
        
        self.event_list_idle = []
        self.event_list_cmd = []
        self.dispensing = 0
        # total dispensed to customer in this session
        self.dispensed = 0
        self.failed_payout_amt = 0
        self.failed_payout_evt = 0
        self.event_counter = 0
        # total received by customer in this session
        self.received = TrackedObject(0)
        self.bill_id_pending = 0
        self.current_bill_status = BillStatus.OUTSIDE
        
        self.cipher_key = bytearray(8)
        self.rng_val = bytearray(b'\x55\x55\x55\x55\x55\x55\x55\x55')
        self.sec_key = bytearray(8)

        self.rc_box1_id = 1
        self.rc_box2_id = 2
        
        self.rc_box1_bill_id = 0
        self.rc_box2_bill_id = 0
        self.rc_box1_total_val = 0
        self.rc_box2_total_val = 0
        # sum of all boxes total
        self.rc_total_val = 0

        self.rc_note_at_entrance = TrackedObject(False)
        self.rc_stat1 = 0
        self.rc_stat2 = 0
        self.rc_box1_stat = 0
        self.rc_box2_stat = 0
        self.rc_remaining_notes = 0
        self.rc_paid_notes = 0
        
        self.serial_no = 0
        self.scaling = 0
        self.denoms = []
        for denom in type(self)._denoms_template:
            denom['cur'] = country
            self.denoms.append(denom)
            
        self.setupComms()
        self.setupPoller()
            

    def __del__(self):
        print("JcmBnv instance deleted", threading.current_thread())
        if inspect.currentframe().f_back is not None:
            print("called from ", inspect.currentframe().f_back.f_code.co_name)

        if threading.current_thread() == self.BPT:
            print("JcmBnv is same as bnvPoller_thread")
        elif self.BPT.is_alive():
            # self.BPT.join(10)
            self.BPT.join()
            print("bnvPoller_thread joined")
        else:
            print("bnvPoller_thread dead")

        if threading.current_thread() == self.EDT:
            print("JcmBnv is same as event_reader_thread")
        elif self.EDT.is_alive():
            # self.EDT.join(10)
            self.EDT.join()
            print("event_reader_thread joined")
        else:
            print("event_reader_thread dead")
            
        if self.fd_ser is not None:
            self.fd_ser.close()
            self.fd_ser = None


    def getCc2Addr(self):
        return pbg.bnv_cc2_address


    def setupComms(self):
        try:
            self.fd_ser = serial.Serial(self.serial_dev, 9600, timeout=0.5)
            print("Opened ", self.fd_ser.name)
        except Exception as exc:
            print("Can't open port to Bnv device: %s", exc)
            raise
            
        self.ev_detect = EventDetect(pbg.ev_shutdown, None, self.fd_ser, self.ev_q)
        self.EDT = threading.Thread(target=self.ev_detect.event_reader_thread, args=(), name='BNV-ED')
        self.ev_detect.set_ser_readline(False)
        self.EDT.start()
        
        self.cc2Helper = Cc2Helper(event_manager=self.ev_detect, cc2echo=True)
            

    def setupPoller(self):
        self.BPT = threading.Thread(target=self.bnvPoller_thread, args=(None, None), name='BNV-Poller') #fixme for queues to the poller
        self.BPT.start()
            
    def initBnv(self):
        # todo global recovery?
        if self.malfunctioned:
            # disable UI button
            pbg.qt_btn1_state_bnv_active.value = False
            self.initialised = False
            return False
            
        if self.initialised:
            return True
            
        # disable UI button
        pbg.qt_btn1_state_bnv_active.value = False

        while pbg.bnvInstance is None:
            time.sleep(self.poll_delay_time)
            print('waiting for bnv Instance to be created...')
        
        if self.cc2Helper.get_parentDeviceObj() is None:
            self.cc2Helper.set_parentDeviceObj(pbg.bnvInstance)
        
        # -------------------------------------------------------------------------------------------------
        # BNV specific INIT start
        # -------------------------------------------------------------------------------------------------
        if not self.cc2Helper.cc2Poll():
            return False
        time.sleep(self.min_delay_time)
        
        succ, data = self.cc2Helper.cc2RequestEncryptionSupport()
        if succ and data is not None:
            print('data returned')
            print_hex(data)
            print_dec(data)
            if ord(data[0]) != 0:
                print('ccTalk protocol level must be unencrypted', ord(data[0]), logl='error')
                self.malfunctioned = True
                return False
            if ord(data[1]) != 101:
                print('ccTalk command level must be DES', ord(data[1]), logl='error')
                self.malfunctioned = True
                return False
        if not succ:
            self.malfunctioned = True
            return False
        time.sleep(self.min_delay_time)
        
        succ, data = self.cc2Helper.cc2RequestSoftwareRevision()
        if succ and data is not None:
            print('data returned')
            print_hex(data)
        if not succ:
            self.malfunctioned = True
            return False
        time.sleep(self.min_delay_time)

        succ, data = self.cc2Helper.cc2RequestSerialNumber()
        if succ and data is not None:
            print('data returned')
            print_hex(data)
        if not succ:
            self.malfunctioned = True
            return False
        time.sleep(self.min_delay_time)

        succ, data = self.cc2Helper.cc2RequestCountryScalingFactor()
        if succ and data is not None:
            print('data returned')
            print_hex(data)
        if not succ:
            self.malfunctioned = True
            return False
        time.sleep(self.min_delay_time)

        for bill_id in range(1, 17):
            succ, data = self.cc2Helper.cc2RequestBillId(bill_id)
            if succ and data is not None:
                print('data returned')
                print_hex(data)
            if not succ:
                self.malfunctioned = True
                return False
            time.sleep(self.min_delay_time)

        succ, data = self.cc2Helper.cc2ModifyBillOperatingMode(stacker=True, escrow=True)
        if succ and data is not None:
            print('data returned')
            print_hex(data)
        if not succ:
            self.malfunctioned = True
            return False
        time.sleep(self.min_delay_time)

        # enable all denoms ...
        self.setInhibitStatus(inhibit=False, denom_value='all')
        # ... bar 2000 and 5000 CZK
        self.setInhibitStatus(inhibit=True, denom_value=200000)
        self.setInhibitStatus(inhibit=True, denom_value=500000)

        succ, data = self.cc2Helper.cc2ModifyInhibitStatus()
        if succ and data is not None:
            print('data returned')
            print_hex(data)
        if not succ:
            self.malfunctioned = True
            return False
        time.sleep(self.min_delay_time)

        # -------------------------------------------------------------------------------------------------
        # BNV specific INIT end
        # -------------------------------------------------------------------------------------------------

        # -------------------------------------------------------------------------------------------------
        # RC specific INIT start
        # -------------------------------------------------------------------------------------------------
        succ, data = self.cc2Helper.cc2PumpRNG(rng_val=random_bytes(8))
        if succ and data is not None:
            print('data returned')
            print_hex(data)
        if not succ:
            self.malfunctioned = True
            return False
        time.sleep(self.min_delay_time)

        succ, data = self.cc2Helper.cc2RequestCipherKey()
        if succ and data is not None:
            print('data returned')
            print_hex(data)
        if not succ:
            self.malfunctioned = True
            return False
        time.sleep(self.min_delay_time)
        print('sec key calculated:')
        print_hex(self.getSessKey())

        # set Bill IDs for the RC Boxes
        succ, data = self.cc2Helper.cc2RequestVariableSet(0)
        if succ and data is not None:
            print('data returned')
            print_hex(data)
        if not succ:
            self.malfunctioned = True
            return False
        time.sleep(self.min_delay_time)
        
        # see if need to modify them...
        box1_denom = self.getDenomDataByBillId(self.rc_box1_bill_id)
        box2_denom = self.getDenomDataByBillId(self.rc_box2_bill_id)
        if box1_denom['val'] == pbg.bnv_rc_denom1_value and box2_denom['val'] == pbg.bnv_rc_denom2_value:
            # good
            pass
        elif box1_denom['val'] == pbg.bnv_rc_denom2_value and box2_denom['val'] == pbg.bnv_rc_denom1_value:
            # good
            pass
        else:
            # not good!
            print('changing settings for bill id in RC boxes', box1_denom, box2_denom)
            box1_denom = self.getDenomDataByValue(pbg.bnv_rc_denom1_value)
            box2_denom = self.getDenomDataByValue(pbg.bnv_rc_denom2_value)
            
            rc_id = [self.rc_box1_id, self.rc_box2_id]
            bill_id = [box1_denom['bill'], box2_denom['bill']]
            
            succ, data = self.cc2Helper.cc2ModifyVariableMCSet(rc_id, bill_id)
            if succ and data is not None:
                print('data returned')
                print_hex(data)
            if not succ:
                self.malfunctioned = True
                return False
            time.sleep(self.min_delay_time)

            # set NEW Bill IDs for the RC Boxes
            succ, data = self.cc2Helper.cc2RequestVariableSet(0)
            if succ and data is not None:
                print('data returned')
                print_hex(data)
            if not succ:
                self.malfunctioned = True
                return False
            time.sleep(self.min_delay_time)

        # set Levels of Notes in RC Boxes
        succ, data = self.cc2Helper.cc2RequestRCCurrentCount(0)
        if succ and data is not None:
            print('data returned')
            print_hex(data)
        if not succ:
            self.malfunctioned = True
            return False
        time.sleep(self.min_delay_time)

        succ, data = self.cc2Helper.cc2RequestRCStatus(0)
        if succ and data is not None:
            print('data returned')
            print_hex(data)
        if not succ:
            self.malfunctioned = True
            return False
        time.sleep(self.min_delay_time)

        # -------------------------------------------------------------------------------------------------
        # RC specific INIT end
        # -------------------------------------------------------------------------------------------------

        succ, data, status_events = self.cc2Helper.cc2ReadBufferedBillEvents()
        if succ:
            print('events returned', status_events)
            (evt_counter, evt_codeA, evt_codeB, evt_type) = status_events[0]
            self.event_counter = evt_counter
            if self.event_counter != 0:
                # todo bnv will most likely have events from past sessions
                # decide what to do with them
                print('BNV has events at INIT time', logl='info')
            else:
                print('BNV event queue is empty')
            self.collectBnvEventsIdle(status_events)
            self.processBnvEventsIdle()
        if not succ:
            self.malfunctioned = True
            return False


        if not self.disableBnv(force=True):
            return False
        
        print('BNV denoms post init:', self.denoms)

        box1_denom = self.getDenomDataByBillId(self.rc_box1_bill_id)
        print('RC Box1 has Notes of Value ', box1_denom['val'])
        print('and quantity ', box1_denom['lvl'])
        print('for total amt ', self.rc_box1_total_val)
        
        box2_denom = self.getDenomDataByBillId(self.rc_box2_bill_id)
        print('RC Box2 has Notes of Value ', box2_denom['val'])
        print('and quantity ', box2_denom['lvl'])
        print('for total amt ', self.rc_box2_total_val)
        
        self.initialised = True
        pbg.qt_btn1_state_bnv_active.value = True
        
        return True
        

    def enableBnv(self):
        if not self.initialised:
            return False
            
        succ, data = self.cc2Helper.cc2GetMasterInhibitStatus()
        if succ and data is not None:
            print('data returned')
            print_hex(data)
            if data[0] == '\x00':
                print('BNV disabled; enabling')
                time.sleep(self.min_delay_time)
                succ, data = self.cc2Helper.cc2SetMasterInhibitStatus(enabled=True)
                if succ and data is not None:
                    print('data returned')
                    print_hex(data)
                if not succ:
                    return False
                    self.malfunctioned = True
            else:
                print('BNV enabled; continuing')
        if not succ:
            self.malfunctioned = True
            return False
        time.sleep(self.min_delay_time)

        succ, data = self.cc2Helper.cc2EnableRC(enable=True)
        if succ and data is not None:
            print('data returned')
            print_hex(data)
        if not succ:
            self.malfunctioned = True
            return False
        time.sleep(self.min_delay_time)

        return True

    def disableBnv(self, force=False):
        if not self.initialised:
            if not force:
                return False
            
        succ, data = self.cc2Helper.cc2GetMasterInhibitStatus()
        if succ and data is not None:
            print('data returned')
            print_hex(data)
            if data[0] == '\x01':
                print('BNV enabled; disabling')
                time.sleep(self.min_delay_time)
                succ, data = self.cc2Helper.cc2SetMasterInhibitStatus(enabled=False)
                if succ and data is not None:
                    print('data returned')
                    print_hex(data)
                if not succ:
                    self.malfunctioned = True
                    return False
            else:
                print('BNV disabled; continuing')
        if not succ:
            self.malfunctioned = True
            return False
        time.sleep(self.min_delay_time)

        return True

    def bnvPoller_thread(self, arg1, arg2):
        self.min_delay_time = pbg.bnv_min_delay_time
        self.poll_delay_time = pbg.bnv_poll_delay_time
        
        while True:
            if pbg.ev_shutdown.is_set():
                break
            if not self.initBnv():
                time.sleep(10 * self.poll_delay_time)
                continue

            try:
                self.bnv_cmd_current = self.bnv_cmd_q.get(timeout=self.poll_delay_time)
                print('bnv got cmd', self.bnv_cmd_current)

                # update Levels of Notes in RC Boxes
                succ, data = self.cc2Helper.cc2RequestRCCurrentCount(0)
                if succ and data is not None:
                    print('data returned')
                    print_hex(data)
                if not succ:
                    self.malfunctioned = True
                    print('RC Count cmd Failed!', logl='warning')
                    continue
                time.sleep(self.min_delay_time)

                print('BNV denoms:', self.denoms)
                self.resetBnvEventsCmd()
                
                if self.bnv_cmd_current['command'] == 'dispense_notes':
                    total_to_dispense = self.bnv_cmd_current['amount']
                    if total_to_dispense == 0:
                        self.bnv_cmd_current['status'] = 'complete'
                        self.bnv_cmd_current['result'] = 'success'
                        self.bnv_cmd_current['message'] = 'Your banknote is accepted'
                        self.bnv_cmd_rsp_q.put(self.bnv_cmd_current)
                        self.bnv_cmd_current = None
                        continue
                    
                    # reset self.rc_note_at_entrance.value_changed
                    if self.rc_note_at_entrance.value:
                        print('Unexpected note at the entrance', logl='warning')
                    
                    box1_denom = self.getDenomDataByBillId(self.rc_box1_bill_id)
                    box2_denom = self.getDenomDataByBillId(self.rc_box2_bill_id)

                    succ, notes_box1, notes_box2 = self.splitRCTotalToNotes(total_to_dispense, 
                        box1_denom['val'], box1_denom['lvl'], box2_denom['val'], box2_denom['lvl'])
                        
                    if not succ:
                        self.bnv_cmd_current['status'] = 'complete'
                        self.bnv_cmd_current['result'] = 'failure'
                        self.bnv_cmd_current['message'] = 'Not enough Notes in RC for payout'
                        self.bnv_cmd_rsp_q.put(self.bnv_cmd_current)
                        self.bnv_cmd_current = None
                    else:
                        if notes_box1 > 0:
                            succ, data = self.cc2Helper.cc2DispenseRCBills(self.rc_box1_id, notes_box1)
                            if succ and data is not None:
                                print('data returned')
                                print_hex(data)
                            if not succ:
                                self.malfunctioned = True
                                print('Dispense Bills cmd Failed!', logl='warning')
                            time.sleep(self.min_delay_time)
                            
                            note_collect_timeout_start_time = None
                            while True:
                                succ, data = self.cc2Helper.cc2RequestRCStatus(0)
                                if succ and data is not None:
                                    print('data returned')
                                    print_hex(data)
                                if not succ:
                                    self.malfunctioned = True
                                    print('Status on Dispense Bills cmd Failed!', logl='warning')
                                    continue
                                    
                                print('Remaining notes box1', self.rc_remaining_notes)
                                print('Paid notes box1', self.rc_paid_notes)
                                print('Note at entrance box1', bool(self.rc_stat1 & BitMask.B6))
                                
                                if self.rc_note_at_entrance.value_changed:
                                    if self.rc_note_at_entrance.value:
                                        note_collect_timeout_start_time = time.time()
                                        self.bnv_cmd_current['status'] = 'executing'
                                        self.bnv_cmd_current['result'] = 'popup_show'
                                        self.bnv_cmd_current['message'] = \
                                            f'Please collect your Banknote {self.rc_paid_notes + 1} out of {notes_box1 + notes_box2}'

                                    else:
                                        note_collect_timeout_start_time = None
                                        self.bnv_cmd_current['status'] = 'executing'
                                        self.bnv_cmd_current['result'] = 'popup_hide'
                                        self.bnv_cmd_current['message'] = ''
                                    self.bnv_cmd_rsp_q.put(self.bnv_cmd_current)

                                if self.rc_remaining_notes == 0:
                                    break
                                    
                                if note_collect_timeout_start_time is not None:
                                    if time.time() - note_collect_timeout_start_time > pbg.note_collect_timeout:
                                        # send note back to BNV
                                        print('Customer failed to collect the note, aborting session', logl='warning')
                                        succ, data = self.cc2Helper.cc2EmergencyStop(0)
                                        if succ and data is not None:
                                            print('data returned')
                                            print_hex(data)
                                        if not succ:
                                            self.malfunctioned = True
                                            print('EmergencyStop cmd Failed!', logl='warning')
                                        time.sleep(self.min_delay_time)
                                        
                                        # force an error
                                        self.rc_paid_notes = 0
                                        break

                                time.sleep(self.poll_delay_time)
                        else:
                            self.rc_paid_notes = 0

                        if self.rc_paid_notes == notes_box1:
                            # success box1
                            print('Payout Box1 success')
                            paid_box1 = self.rc_paid_notes
                            
                            if notes_box2 > 0:
                                succ, data = self.cc2Helper.cc2DispenseRCBills(self.rc_box2_id, notes_box2)
                                if succ and data is not None:
                                    print('data returned')
                                    print_hex(data)
                                if not succ:
                                    self.malfunctioned = True
                                    print('Dispense Bills cmd Failed!', logl='warning')
                                time.sleep(self.min_delay_time)
                                
                                note_collect_timeout_start_time = None
                                while True:
                                    succ, data = self.cc2Helper.cc2RequestRCStatus(0)
                                    if succ and data is not None:
                                        print('data returned')
                                        print_hex(data)
                                    if not succ:
                                        self.malfunctioned = True
                                        print('Status on Dispense Bills cmd Failed!', logl='warning')
                                        continue

                                    print('Remaining notes box2', self.rc_remaining_notes)
                                    print('Paid notes box2', self.rc_paid_notes)
                                    print('Note at entrance box2', bool(self.rc_stat1 & BitMask.B6))
                                
                                    if self.rc_note_at_entrance.value_changed:
                                        if self.rc_note_at_entrance.value:
                                            note_collect_timeout_start_time = time.time()
                                            self.bnv_cmd_current['status'] = 'executing'
                                            self.bnv_cmd_current['result'] = 'popup_show'
                                            self.bnv_cmd_current['message'] = \
                                                f'Please collect your Banknote {paid_box1 + self.rc_paid_notes + 1} out of {notes_box1 + notes_box2}'
                                        else:
                                            note_collect_timeout_start_time = None
                                            self.bnv_cmd_current['status'] = 'executing'
                                            self.bnv_cmd_current['result'] = 'popup_hide'
                                            self.bnv_cmd_current['message'] = ''
                                        self.bnv_cmd_rsp_q.put(self.bnv_cmd_current)
                                        
                                    if self.rc_remaining_notes == 0:
                                        break
                                        
                                    if note_collect_timeout_start_time is not None:
                                        if time.time() - note_collect_timeout_start_time > pbg.note_collect_timeout:
                                            # send note back to BNV
                                            print('Customer failed to collect the note, aborting session', logl='warning')
                                            succ, data = self.cc2Helper.cc2EmergencyStop(0)
                                            if succ and data is not None:
                                                print('data returned')
                                                print_hex(data)
                                            if not succ:
                                                self.malfunctioned = True
                                                print('EmergencyStop cmd Failed!', logl='warning')
                                            time.sleep(self.min_delay_time)
                                            
                                            # force an error
                                            self.rc_paid_notes = 0
                                            break
                                        
                                    time.sleep(self.poll_delay_time)
                            else:
                                self.rc_paid_notes = 0

                            if self.rc_paid_notes == notes_box2:
                                # success box2
                                print('Payout Box2 success')
                                self.bnv_cmd_current['status'] = 'complete'
                                self.bnv_cmd_current['result'] = 'success'
                            else:
                                # failure box2
                                print('Payout Box2 Failed!', logl='warning')
                                self.bnv_cmd_current['status'] = 'complete'
                                self.bnv_cmd_current['result'] = 'failure'
                        else:
                            # failure box1
                            print('Payout Box1 Failed!', logl='warning')
                            self.bnv_cmd_current['status'] = 'complete'
                            self.bnv_cmd_current['result'] = 'failure'

                        self.bnv_cmd_rsp_q.put(self.bnv_cmd_current)
                        self.bnv_cmd_current = None
                    print('dispense notes handler finished')
                    
                elif self.bnv_cmd_current['command'] == 'accept_notes_start':
                    # reset self.rc_note_at_entrance.value_changed
                    if self.rc_note_at_entrance.value:
                        print('Unexpected note at the entrance', logl='warning')
                        
                    if self.enableBnv():
                        #self.bnv_cmd_current['status'] = 'complete'
                        #self.bnv_cmd_current['result'] = 'success'
                        self.bnv_cmd_current['status'] = 'executing'
                        self.bnv_cmd_current['result'] = 'unavailable'
                        self.bnv_cmd_current['amount'] = self.received.value
                    else:
                        self.bnv_cmd_current['status'] = 'complete'
                        self.bnv_cmd_current['result'] = 'failure'
                        self.bnv_cmd_current['amount'] = self.received.value
                        self.bnv_cmd_rsp_q.put(self.bnv_cmd_current)
                        self.bnv_cmd_current = None
                    
                elif self.bnv_cmd_current['command'] == 'accept_notes_stop':
                    if self.disableBnv():
                        self.bnv_cmd_current['status'] = 'complete'
                        self.bnv_cmd_current['result'] = 'success'
                        self.bnv_cmd_current['amount'] = self.received.value
                    else:
                        self.bnv_cmd_current['status'] = 'complete'
                        self.bnv_cmd_current['result'] = 'failure'
                        self.bnv_cmd_current['amount'] = self.received.value
                    self.bnv_cmd_rsp_q.put(self.bnv_cmd_current)
                    self.bnv_cmd_current = None
                    
                    self.resetTotalReceived()
                else:
                    print("no handler for bnv cmd", self.bnv_cmd_current)
                    
                
            except queue.Empty:
                self.cc2Helper.quiet = True
                succ, data, status_events = self.cc2Helper.cc2ReadBufferedBillEvents()
                if succ:
                    #print('events returned', status_events)
                    self.collectBnvEventsIdle(status_events)
                    self.processBnvEventsIdle()
                else:
                    self.malfunctioned = True
                self.cc2Helper.quiet = False
                
                #print('current bill status', self.current_bill_status)
                
                if self.current_bill_status == BillStatus.IN_ESCROW:
                    always_route_in = False
                    if self.bnv_cmd_current is None:
                        print('bill in escrow but no cur bnv cmd', logl='warning')
                    else:
                        if self.bnv_cmd_current['command'] == 'accept_notes_start':
                            if not self.bnv_cmd_current['check_dispense_values']:
                                always_route_in = True
                                print('always_route_in overridden', always_route_in)
                            else:
                                print('always_route_in NOT overridden', always_route_in)
                                pass
                        else:
                            print('always_route_in not overridden for cmd', self.bnv_cmd_current['command'])
                
                    if not always_route_in:
                        box1_denom = self.getDenomDataByBillId(self.rc_box1_bill_id)
                        box2_denom = self.getDenomDataByBillId(self.rc_box2_bill_id)
                        escrow_bill_denom = self.getDenomDataByBillId(self.bill_id_pending)
                        escrow_val = escrow_bill_denom['val']
                        if escrow_val == 10000:
                            future_dispense_val = escrow_val - pbg.coinsFor100
                        elif escrow_val == 20000:
                            future_dispense_val = escrow_val - pbg.coinsFor200
                        elif escrow_val == 50000:
                            future_dispense_val = escrow_val - pbg.coinsFor500
                        elif escrow_val == 100000:
                            # todo worry about 'flexible' exchange?
                            # calc max possible future_dispense_val
                            
                            if pbg.fixedExchangeScheme:
                                if pbg.flexible1000Exchange:
                                    future_dispense_val = escrow_val - min(pbg.coinsFor1000, pbg.coinsFor1000Alt) #foolproof!!
                                else:
                                    future_dispense_val = escrow_val - pbg.coinsFor1000
                            else:
                                future_dispense_val = escrow_val - pbg.minExchangeAmount

                        succ, _, _ = self.splitRCTotalToNotes(future_dispense_val, 
                            box1_denom['val'], box1_denom['lvl'], box2_denom['val'], box2_denom['lvl'])
                    else:
                        succ = True
                        
                    if not succ:
                        print('No notes in RC for change, routing bill out', logl='warning')
                        time.sleep(self.min_delay_time)
                        succ, data = self.cc2Helper.cc2RouteBill(return_bill=True)
                        if succ and data is not None:
                            print('data returned')
                            print_hex(data)
                        if not succ:
                            self.malfunctioned = True
                            print('Route Bill cmd Failed!', logl='warning')
                            continue

                        note_collect_timeout_start_time = None
                        while True:
                            time.sleep(self.min_delay_time)
                            succ, data = self.cc2Helper.cc2RequestRCStatus(0)
                            if succ and data is not None:
                                print('data returned')
                                print_hex(data)
                            if not succ:
                                self.malfunctioned = True
                                print('Status on Route Bill cmd Failed!', logl='warning')
                                continue

                            print('Escrow Note at entrance ', bool(self.rc_stat1 & BitMask.B6))
                        
                            if self.rc_note_at_entrance.value_changed:
                                if self.bnv_cmd_current is None:
                                    print('rc_note_at_entrance.value_changed but no cur bnv cmd', logl='error')
                                else:
                                    if self.bnv_cmd_current['command'] != 'accept_notes_start':
                                        print('Unexpected cmd while routing bill out', self.bnv_cmd_current, logl='warning')
                                    
                                    if self.rc_note_at_entrance.value:
                                        note_collect_timeout_start_time = time.time()
                                        self.bnv_cmd_current['status'] = 'executing'
                                        self.bnv_cmd_current['result'] = 'popup_show'
                                        self.bnv_cmd_current['message'] = \
                                            'Unable to change your Banknote\nPlease try smaller denomination'
                                        self.bnv_cmd_rsp_q.put(self.bnv_cmd_current)
                                    else:
                                        note_collect_timeout_start_time = None
                                        self.bnv_cmd_current['status'] = 'executing'
                                        self.bnv_cmd_current['result'] = 'popup_hide'
                                        self.bnv_cmd_current['message'] = ''
                                        self.bnv_cmd_rsp_q.put(self.bnv_cmd_current)
                                        break
                                
                            if note_collect_timeout_start_time is not None:
                                if time.time() - note_collect_timeout_start_time > pbg.note_collect_timeout:
                                    # can't send note back to BNV
                                    print('Customer failed to collect the note, aborting session', logl='warning')
                                    time.sleep(self.min_delay_time)
                                    # todo cc2EmergencyStop doesn't seem to work in this case
                                    # regardless of whether bnv is disabled or not
                                    #self.disableBnv()
                                    succ, data = self.cc2Helper.cc2ResetDevice()
                                    if succ and data is not None:
                                        print('data returned')
                                        print_hex(data)
                                    if not succ:
                                        self.malfunctioned = True
                                        print('cc2ResetDevice cmd Failed!', logl='warning')
                                        
                                    self.bnv_cmd_current['status'] = 'executing'
                                    self.bnv_cmd_current['result'] = 'popup_hide'
                                    self.bnv_cmd_current['message'] = ''
                                    print('sending', self.bnv_cmd_current)
                                    self.bnv_cmd_rsp_q.put(self.bnv_cmd_current)
                                    # todo racing condition here, investigate
                                    time.sleep(self.poll_delay_time)
                                    self.bnv_cmd_current['status'] = 'complete'
                                    self.bnv_cmd_current['result'] = 'failure'
                                    self.bnv_cmd_current['message'] = ''
                                    print('sending', self.bnv_cmd_current)
                                    self.bnv_cmd_rsp_q.put(self.bnv_cmd_current)
                                    # force re-init
                                    self.initialised = False
                                    break
                            time.sleep(self.poll_delay_time)
                    
                    else:
                        time.sleep(self.min_delay_time)
                        succ, data = self.cc2Helper.cc2RouteBill()
                        if succ and data is not None:
                            print('data returned')
                            print_hex(data)
                        if not succ:
                            self.malfunctioned = True
                        time.sleep(self.min_delay_time)
                    
                if self.received.value_changed:
                    if self.bnv_cmd_current is None:
                        dummy_received = self.received.value
                        print('received.value_changed but no cur bnv cmd', dummy_received, logl='warning')
                    else:
                        if self.bnv_cmd_current['command'] == 'accept_notes_start':
                            self.bnv_cmd_current['status'] = 'executing'
                            self.bnv_cmd_current['result'] = 'unavailable'
                            self.bnv_cmd_current['amount'] = self.received.value
                            self.bnv_cmd_rsp_q.put(self.bnv_cmd_current)
                        else:
                            print('bnv_cmd_current is wrong - ', self.bnv_cmd_current)
                            # reset 'value changed'
                            dummy_received = self.received.value
            
            except:
                print("Unexpected error:", sys.exc_info()[0], logl='error')
                self.malfunctioned = True
                raise
                break
                
        print('poller loop exited')

    def initDenoms(self, denom_data):
        self.denoms = []
        num_denoms = ord(denom_data[0])
        denom_rec_size = 7 # 4 value + 3 ccode
        
        for rec_no in range(num_denoms):
            denom_rec_data = denom_data[1+rec_no*denom_rec_size:1+(rec_no+1)*denom_rec_size]
            denom = {}
            denom['val'] = struct.unpack('<I', s2b(denom_rec_data[0:4]))[0]
            denom['lvl'] = 0
            denom['cur'] = denom_rec_data[4:7]
            denom['rut'] = -1
            denom['qty'] = 0
            self.denoms.append(denom)
            
    def setLevels(self, level_data):
        # bill ids must be initialised before this call!
        box1_succ = False
        box2_succ = False

        for i in range(len(self.denoms)):
            denom = self.denoms[i]
            if denom['bill'] == self.rc_box1_bill_id:
                denom['lvl'] = struct.unpack('<H', s2b(level_data[0:2]))[0]
                self.denoms[i] = denom
                self.rc_box1_total_val = denom['lvl'] * denom['val']
                box1_succ = True
                
            if denom['bill'] == self.rc_box2_bill_id:
                denom['lvl'] = struct.unpack('<H', s2b(level_data[2:4]))[0]
                self.denoms[i] = denom
                self.rc_box2_total_val = denom['lvl'] * denom['val']
                box2_succ = True
                
            if box1_succ and box2_succ:
                break

        #self.updateRCTotal()
        self.rc_total_val = self.rc_box1_total_val + self.rc_box2_total_val
        
        if box1_succ and box2_succ:
            return True
            
        return False

    def setRCBoxBillIds(self, bill_id_data):
        self.rc_box1_bill_id = struct.unpack('<H', s2b(bill_id_data[0:2]))[0]
        self.rc_box2_bill_id = struct.unpack('<H', s2b(bill_id_data[2:4]))[0]


    def resetQuantityAll(self):
        for i in range(len(self.denoms)):
            denom = self.denoms[i]
            denom['qty'] = 0
            self.denoms[i] = denom

    def setQuantityVal(self, quantity, value):
        for i in range(len(self.denoms)):
            denom = self.denoms[i]
            if denom['val'] == value:
                denom['qty'] = quantity
                self.denoms[i] = denom
                break


    def collectBnvEventsCmd(self, status_events):
        for evt in status_events:
            evt_code, evt_data, evt_type = evt
            if evt_code == 0:
                # ignore idle status
                continue
            self.event_list_cmd.append(evt)
        
    def resetBnvEventsCmd(self):
        self.event_list_cmd = []
        self.dispensing = 0
        self.dispensed = 0
        self.failed_payout_amt = 0
        self.failed_payout_evt = 0
        
    def processBnvEventsCmd(self):
        failed_payout_events = [5,6,9,16]
        idle_events = [10,13,16,17,19,54,58]
        
        for evt in self.event_list_cmd:
            evt_code, evt_data, evt_type = evt
            if evt_code == 2:
                # dispensed
                self.dispensed = struct.unpack('<I', s2b(evt_data))[0]
            elif evt_code == 1:
                # dispensing - save max last known amount
                dispensing = struct.unpack('<I', s2b(evt_data))[0]
                if self.dispensing < dispensing:
                    self.dispensing = dispensing
            elif evt_code in failed_payout_events:
                # payout failed - save max last known amount
                self.failed_payout_amt = struct.unpack('<I', s2b(evt_data))[0]
                self.failed_payout_evt = evt_code
            elif evt_code in idle_events:
                # events not related to payout - forward to idle collector
                self.collectBnvEventsIdle(evt)
            elif evt_code == 12:
                # cashbox paid - not used
                continue
            else:
                print("Unexpected event:", evt, logl='warning')

    def collectBnvEventsIdle(self, status_events):
        '''
            (evt_counter, evt_codeA, evt_codeB, evt_type) = status_events[0]
            self.event_counter = evt_counter
            
            evt_counter is the same for all event in the message and is the last event's counter
            in our internal list we restore the correct counter values per event
            
            events are cycled like so:
            
            0 0 0
            1 0 0 
            2 1 0
            3 2 1

            254 253 252
            255 254 253
            1 255 254
            2 1 255
            3 2 1                                 
            
            3 2 1 0 0 -> 0 0 1 2 3
        '''
        (evt_counter, evt_codeA, evt_codeB, evt_type) = status_events[0]
        if evt_counter == self.event_counter:
            # no new events
            return
        if evt_counter < self.event_counter:
            new_events_num = evt_counter + 255 - self.event_counter
        else:
            new_events_num = evt_counter - self.event_counter
            
        self.event_counter = evt_counter
        
        historic_status_events = list(reversed(status_events))
        
        for evt in historic_status_events[5 - new_events_num:]:
            if new_events_num == 0:
                break

            evt_counter, evt_codeA, evt_codeB, evt_type = evt
            # evt_counter can be zero or negative, but as long as they are mathematically sorted
            # i don't feel the urge to produce correct source sequence like 2 1 255 254 253
            # maybe a todo though :)
            evt_counter -= new_events_num - 1
            evt = (evt_counter, evt_codeA, evt_codeB, evt_type)

            self.event_list_idle.append(evt)
            new_events_num -= 1

    def processBnvEventsIdle(self):
        for evt in self.event_list_idle:
            evt_counter, evt_codeA, evt_codeB, evt_type = evt
            print("Processing event:", evt, logl='info')
            
            if evt_codeA == 0:
                # status or error
                if evt_codeB in [4,5]:
                    # inhibited bill
                    pass
                elif evt_codeB == 1:
                    # bill returned from escrow
                    self.current_bill_status = BillStatus.OUTSIDE
            else:
                # credit or pending credit
                #if evt_codeB == 0:
                if evt_codeB in [0,30,31,32]:
                    # topup customer balance with credit
                    if self.current_bill_status == BillStatus.ROUTING_IN:
                        # bill just came from escrow
                        print('Routed in bill', self.bill_id_pending)
                        self.bill_id_pending = 0
                    self.addReceived(evt_codeA)
                    self.current_bill_status = BillStatus.INSIDE
                elif evt_codeB == 1:
                    # route to stacker/cashbox if all is good
                    self.bill_id_pending = evt_codeA
                    self.current_bill_status = BillStatus.IN_ESCROW
                    print('Escrow has bill', self.bill_id_pending)
                else:
                    print("Unexpected event:", evt, logl='warning')
                
        self.event_list_idle = []

    def setSerialNumber(self, serial):
        #self.serial_no = serial[0] + 256 * serial[1] + 65536 * serial[2]
        self.serial_no = ord(serial[0]) + 256 * ord(serial[1]) + 65536 * ord(serial[2])
        print('BNV serial is', self.serial_no)

    def setScalingFactor(self, scaling_factor):
        self.scaling = scaling_factor
        print('BNV scaling is', self.scaling)

    def setBillId(self, bill_id, denom):
        # convert 'CZ0100A' into denom and set bill id for it
        country2 = denom[0:2]
        if country2 == self.country:
            try:
                value = self.scaling * int(denom[2:6])
                
                for i in range(len(self.denoms)):
                    denom = self.denoms[i]
                    if denom['val'] == value:
                        denom['bill'] = bill_id
                        self.denoms[i] = denom
                        break
            except ValueError:
                print('bill id not configured', bill_id)
        else:
            print('invalid country for bill', bill_id, country2, self.country)
        
        
    def getDenomDataByBillId(self, bill_id):
        for i in range(len(self.denoms)):
            denom = self.denoms[i]
            if denom['bill'] == bill_id:
                return denom
        return { 'val': 0, 'lvl': 0, 'cur': 'xxx', 'bill': 0, 'inht': 0, 'rcvd': 0 }
        
        
    def getDenomDataByValue(self, denom_val):
        for i in range(len(self.denoms)):
            denom = self.denoms[i]
            if denom['val'] == denom_val:
                return denom
        return { 'val': 0, 'lvl': 0, 'cur': 'xxx', 'bill': 0, 'inht': 0, 'rcvd': 0 }
        
        
    def addReceived(self, bill_id):
        for i in range(len(self.denoms)):
            denom = self.denoms[i]
            if denom['bill'] == bill_id:
                denom['rcvd'] += 1
                self.denoms[i] = denom
                self.updateTotalReceived(denom['val'])
                break
        
    def updateTotalReceived(self, value):
        # this dancing around with values is because
        # reading the tracked object value will reset
        # its 'value changed' attribute
        old_value = self.received.value
        new_value = value + old_value
        self.received.value = new_value
        print('received', value)
        print('total now', new_value)
        
        
    def resetTotalReceived(self):
        self.received.value = 0
        # reset 'value changed'
        reset_value = self.received.value
        print('totals reset')
        
    def getInhibitStatus(self):
        bitval1 = 0
        for bill_id in range(1, 9):
            for i in range(len(self.denoms)):
                denom = self.denoms[i]
                if denom['bill'] == bill_id:
                    bitval1 += denom['inht'] << (bill_id - 1)
                    break
        
        bitval2 = 0
        for bill_id in range(9, 17):
            for i in range(len(self.denoms)):
                denom = self.denoms[i]
                if denom['bill'] == bill_id:
                    bitval2 += denom['inht'] << (bill_id - 9)
                    break
                    
        return bitval1, bitval2
        
        
    def setInhibitStatus(self, inhibit=True, denom_value='all'):
        # inhibit True means denom['inht'] must be set to 0!
        # denom_value must be 'de-scaled', i.e. 500000 for 5000CZK notes
        if inhibit:
            inhibit_val = 0
        else:
            inhibit_val = 1
            
        for i in range(len(self.denoms)):
            denom = self.denoms[i]
            if denom_value =='all':
                denom['inht'] = inhibit_val
                self.denoms[i] = denom
            else:
                if denom['val'] == denom_value:
                    denom['inht'] = inhibit_val
                    self.denoms[i] = denom
                    break

    def getSessKey(self):
        # generate sec key to dispense bills
        for byte_offset in range(8):
            shifted_byte = lcs(self.cipher_key[byte_offset], 2)
            self.sec_key[byte_offset] = (shifted_byte + self.rng_val[byte_offset]) % 256

        return self.sec_key

    def saveSessKey(self, cipher_key):
        # save cipher key
        self.cipher_key = s2b(cipher_key[0:8])

    def processRCStatus(self, status_data):
        self.rc_stat1 = ord(status_data[0])
        self.rc_stat2 = ord(status_data[1])
        self.rc_box1_stat = ord(status_data[2])
        self.rc_box2_stat = ord(status_data[3])
        '''
        status_data[4]   EVENT CNT Event counter
        status_data[5]   REMAIN CNT Remaining note to be paid out
        status_data[6]   PAID CNT Notes already paid out
        status_data[7]   UNPAID CNT Notes not paid out
        status_data[8]   STORED CNT No. of already collected notes
        status_data[9]   STORE CNT No. of notes being collected
        status_data[10]  PAY REJECT CNT Notes being collected due to Dispense Reject
        status_data[11]  PAY REJECTED CNT Notes already collected due to Dispense Reject
        '''
        self.rc_remaining_notes = ord(status_data[5])
        self.rc_paid_notes = ord(status_data[6])
        self.rc_note_at_entrance.value = bool(self.rc_stat1 & BitMask.B6)

    def splitRCTotalToNotes(self, total_to_dispense, box1_val, box1_lvl, box2_val, box2_lvl):
        # figure out best way to pay the total from notes in both rc boxes
        # pay max from box with bigger value - the rest from the other box
        
        if total_to_dispense == 0:
            # early happy nothing exit
            return True, 0, 0
        
        box1_stored_val = box1_val * box1_lvl
        box2_stored_val = box2_val * box2_lvl
        
        if box2_val > box1_val:
            if total_to_dispense > box2_stored_val:
                # empty box2; the rest from box1
                total_to_dispense_box2 = box2_stored_val
                total_to_dispense_box1 = total_to_dispense - total_to_dispense_box2
            else:
                # max from box2; the rest from box1
                rem = total_to_dispense % box2_val
                if rem == 0:
                    total_to_dispense_box2 = total_to_dispense
                    total_to_dispense_box1 = 0
                else:
                    total_to_dispense_box2 = total_to_dispense - rem
                    total_to_dispense_box1 = rem
        else:
            # 'swop' boxes and use the same algorythm
            if total_to_dispense > box1_stored_val:
                # empty box1; the rest from box2
                total_to_dispense_box1 = box1_stored_val
                total_to_dispense_box2 = total_to_dispense - total_to_dispense_box1
            else:
                # max from box1; the rest from box2
                rem = total_to_dispense % box1_val
                if rem == 0:
                    total_to_dispense_box1 = total_to_dispense
                    total_to_dispense_box2 = 0
                else:
                    total_to_dispense_box1 = total_to_dispense - rem
                    total_to_dispense_box2 = rem
            
        notes_box1 = total_to_dispense_box1/box1_val
        notes_box2 = total_to_dispense_box2/box2_val
        
        if notes_box1 <= box1_lvl and notes_box2 <= box2_lvl:
            print('Total to dispense', total_to_dispense)
            print('Split as qty, val, qty, val', int(total_to_dispense_box1//box1_val), box1_val, int(total_to_dispense_box2//box2_val), box2_val)
            return True, int(total_to_dispense_box1//box1_val), int(total_to_dispense_box2//box2_val)
        else:
            print('Splitting failed', total_to_dispense, int(notes_box1), box1_lvl, int(notes_box2), box2_lvl, logl='warning')
            return False, -1, -1


