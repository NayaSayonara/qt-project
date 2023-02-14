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
#import bbcc2 as bb
from eventdetect import EventDetect
#from cc2fun import *
from cc2helper import Cc2Helper
from trackedobject import TrackedObject


hopper_commands = \
[
{
    # request
    'command': 'payout_amount',
    'amount': 0,
    # response
    'result': 'unknown',
    'status': 'unknown',
    'message': '',
},
]

def get_hopper_cmd_template(cmd):
    for i in range(len(hopper_commands)):
        hopper_command = hopper_commands[i]
        if hopper_command['command'] == cmd:
            return copy.deepcopy(hopper_command)


class SmartHopper:
    _denoms_template = \
    [
    {
        'val': 1,
        'lvl': 0,
        'cur': 'xxx',
        'rut': -1,
        'qty': 0,
    },
    {
        'val': 2,
        'lvl': 0,
        'cur': 'xxx',
        'rut': -1,
        'qty': 0,
    },
    {
        'val': 5,
        'lvl': 0,
        'cur': 'xxx',
        'rut': -1,
        'qty': 0,
    },
    {
        'val': 10,
        'lvl': 0,
        'cur': 'xxx',
        'rut': -1,
        'qty': 0,
    },
    {
        'val': 20,
        'lvl': 0,
        'cur': 'xxx',
        'rut': -1,
        'qty': 0,
    },
    {
        'val': 50,
        'lvl': 0,
        'cur': 'xxx',
        'rut': -1,
        'qty': 0,
    },
    {
        'val': 100,
        'lvl': 0,
        'cur': 'xxx',
        'rut': -1,
        'qty': 0,
    },
    {
        'val': 200,
        'lvl': 0,
        'cur': 'xxx',
        'rut': -1,
        'qty': 0,
    },
    ]
    
    def __init__(self, country='GBP', serial="/dev/ttyUSB0"):
        self.ev_detect = None
        self.serial_dev = serial
        self.fd_ser = None
        self.EDT = None
        self.HPT = None
        self.ev_q = queue.Queue()
        self.initialised = False
        # global 'working' flag for Hopper
        # misconfiguration, no/bad replies etc - all goes here
        # todo this flag is never reset back to False!
        self.malfunctioned = False
        
        self.hopper_cmd_q = queue.Queue()
        self.hopper_cmd_rsp_q = queue.Queue()
        self.hopper_cmd_current = None
        
        self.min_delay_time = 0
        self.poll_delay_time = 0
        self.cc2Helper = None
        
        self.event_list_idle = []
        self.event_list_cmd = []
        self.dispensing = 0
        self.dispensed = 0
        self.failed_payout_amt = 0
        self.failed_payout_evt = 0
        
        self.denoms = []
        for denom in type(self)._denoms_template:
            denom['cur'] = country
            self.denoms.append(denom)
            
        self.setupComms()
        self.setupPoller()
            

    def __del__(self):
        print("SmartHopper instance deleted", threading.current_thread())
        '''
        print(inspect)
        print(inspect.currentframe())
        print(inspect.currentframe().f_back)
        print(inspect.currentframe().f_back.f_code)
        print(inspect.currentframe().f_back.f_code.co_name)
        '''
        if inspect.currentframe().f_back is not None:
            print("called from ", inspect.currentframe().f_back.f_code.co_name)

        if threading.current_thread() == self.HPT:
            print("SmartHopper is same as hopperPoller_thread")
        elif self.HPT.is_alive():
            # self.HPT.join(10)
            self.HPT.join()
            print("hopperPoller_thread joined")
        else:
            print("hopperPoller_thread dead")

        if threading.current_thread() == self.EDT:
            print("SmartHopper is same as event_reader_thread")
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
        return pbg.hopper_cc2_address


    def setupComms(self):
        try:
            self.fd_ser = serial.Serial(self.serial_dev, 9600, timeout=0.5)
            print("Opened ", self.fd_ser.name)
        except Exception as exc:
            print("Can't open port to Hopper device: %s", exc)
            raise
            
        self.ev_detect = EventDetect(pbg.ev_shutdown, None, self.fd_ser, self.ev_q)
        self.EDT = threading.Thread(target=self.ev_detect.event_reader_thread, args=(), name='HOPPER-ED')
        self.ev_detect.set_ser_readline(False)
        self.EDT.start()
        
        self.cc2Helper = Cc2Helper(event_manager=self.ev_detect)
            

    def setupPoller(self):
        self.HPT = threading.Thread(target=self.hopperPoller_thread, args=(None, None), name='HOPPER-Poller') #fixme for queues to the poller
        self.HPT.start()
            
    def initHopper(self):
        # todo global recovery?
        if self.malfunctioned:
            # disable UI button
            pbg.qt_btn1_state_hopper_active.value = False
            self.initialised = False
            return False

        if self.initialised:
            return True
            
        # disable UI button
        pbg.qt_btn1_state_hopper_active.value = False

        while pbg.hopperInstance is None:
            time.sleep(self.poll_delay_time)
            print('waiting for hopper Instance to be created...')
        
        if self.cc2Helper.get_parentDeviceObj() is None:
            self.cc2Helper.set_parentDeviceObj(pbg.hopperInstance)
        
        if not self.cc2Helper.cc2Poll():
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

        # fill in denoms that are set in SH3
        succ, data = self.cc2Helper.cc2GetDeviceSetup_Cur()
        if succ and data is not None:
            print('data returned')
            print_hex(data)
            print('denoms updated', self.denoms)
        if not succ:
            self.malfunctioned = True
            return False
        time.sleep(self.min_delay_time)
        
        # cc2.py for bit meaning
        opt1 = 0b00100111 # unknown to payout; free pay
        #opt1 = 0b00110110 # unknown to payout
        #opt1 = 0b00010110 # unknown to cashbox
        opt2 = 0b00000000 # smart empty to cashbox 
        #opt2 = 0b00001000 # smart empty to payout
        succ, data = self.cc2Helper.cc2SetPayoutOptions(opt1, opt2)
        if succ and data is not None:
            print('data returned')
            print_hex(data)
        if not succ:
            self.malfunctioned = True
            return False
        time.sleep(self.min_delay_time)
        
        succ, data = self.cc2Helper.cc2GetPayoutOptions()
        if succ and data is not None:
            print('data returned')
            print_hex(data)
        if not succ:
            self.malfunctioned = True
            return False
        time.sleep(self.min_delay_time)
        
        succ, data = self.cc2Helper.cc2GetMasterInhibitStatus()
        if succ and data is not None:
            print('data returned')
            print_hex(data)
            if data[0] == '\x00':
                print('SH3 disabled; enabling')
                time.sleep(self.min_delay_time)
                succ, data = self.cc2Helper.cc2SetMasterInhibitStatus(enabled=True)
                if succ and data is not None:
                    print('data returned')
                    print_hex(data)
                if not succ:
                    self.malfunctioned = True
                    return False
            else:
                print('SH3 enabled; continuing')
        if not succ:
            self.malfunctioned = True
            return False
        time.sleep(self.min_delay_time)

        succ, data, status_events = self.cc2Helper.cc2RequestStatus()
        if succ:
            print('events returned', status_events)
            latest_event = status_events[0]
            evt_code, evt_data, evt_type = latest_event
            if evt_code == 0:
                print('status idle')
            else:
                print('status NOT idle')
            self.collectHopperEventsIdle(status_events)
            self.processHopperEventsIdle()
        if not succ:
            self.malfunctioned = True
            return False
        time.sleep(self.min_delay_time)

        # 0=payout, 1=cashbox
        self.setRoutingAll(0)

        succ = self.cc2Helper.cc2SetRouting_Cur()
        if succ:
            print('routing set')
        else:
            print('error!')
        if not succ:
            self.malfunctioned = True
            return False
        time.sleep(self.min_delay_time)

        succ = self.cc2Helper.cc2ResetDenominationAmount_Cur()
        if succ:
            print('levels reset')
        else:
            print('error!')
        if not succ:
            self.malfunctioned = True
            return False
        time.sleep(self.min_delay_time)

        succ = self.cc2Helper.cc2AddDenominationAmount_Cur(level=20)
        if succ:
            print('levels updated', self.denoms)
        else:
            print('error!')
        if not succ:
            self.malfunctioned = True
            return False
        time.sleep(self.min_delay_time)

        succ = self.cc2Helper.cc2GetDenominationAmount_Cur()
        if succ:
            print('levels retreived', self.denoms)
        else:
            print('error!')
        if not succ:
            self.malfunctioned = True
            return False
        time.sleep(self.min_delay_time)
        
        self.initialised = True
        pbg.qt_btn1_state_hopper_active.value = True
        return True


    def hopperPoller_thread(self, arg1, arg2):
        self.min_delay_time = pbg.hopper_min_delay_time
        self.poll_delay_time = pbg.hopper_poll_delay_time
        
        # sh3 fw SH0003 631 2311 000
        
        # if Currency Code (Alpha) is given then template will be
        # used to fill in denoms; otherwise 'get device setup' cmd
        # must be used before setting levels etc
        #smartHopper = SmartHopper()
        
        #self.initHopper()
        
        while True:
            if pbg.ev_shutdown.is_set():
                break
            #if True:
            if not self.initHopper():
                time.sleep(10 * self.poll_delay_time)
                continue
            try:
                self.hopper_cmd_current = self.hopper_cmd_q.get(timeout=self.poll_delay_time)
                print('hopper got cmd', self.hopper_cmd_current)
                self.resetHopperEventsCmd()
                
                if self.hopper_cmd_current['command'] == 'payout_amount':
                    # todo check levels etc
                    succ, data = self.cc2Helper.cc2PayoutAmount(self.hopper_cmd_current['amount'])
                    if not succ:
                        self.malfunctioned = True
                        print('Payout Amount cmd Failed!', logl='warning')
                    time.sleep(self.poll_delay_time)
                    
                    while True:
                        succ, data, status_events = self.cc2Helper.cc2RequestStatus()
                        if succ:
                            #print('events returned', status_events)
                            self.collectHopperEventsCmd(status_events)
                            
                            latest_event = status_events[0]
                            evt_code, evt_data, evt_type = latest_event
                            if evt_code == 0:
                                #print('status idle')

                                self.processHopperEventsCmd()
                                if self.dispensed == self.hopper_cmd_current['amount']:
                                    self.hopper_cmd_current['status'] = 'complete'
                                    self.hopper_cmd_current['result'] = 'success'
                                else:
                                    self.hopper_cmd_current['status'] = 'complete'
                                    self.hopper_cmd_current['result'] = 'failure'
                                    if self.failed_payout_amt > 0:
                                        self.hopper_cmd_current['message'] = 'Sorry we still owe you' + \
                                        dot_amt(str(self.failed_payout_amt)) + ' ' + pbg.currency
                                
                                self.hopper_cmd_rsp_q.put(self.hopper_cmd_current)
                                break
                            else:
                                print('status NOT idle')
                                print('events returned', status_events)
                        else:
                            self.malfunctioned = True
                            
                        time.sleep(self.poll_delay_time)
                else:
                    print("no handler for hopper cmd", self.hopper_cmd_current)
                    
                
            except queue.Empty:
                self.cc2Helper.quiet = True
                succ, data, status_events = self.cc2Helper.cc2RequestStatus()
                if succ:
                    #print('events returned', status_events)
                    latest_event = status_events[0]
                    evt_code, evt_data, evt_type = latest_event
                    if evt_code == 0:
                        #print('status idle')
                        pass
                    else:
                        print('status NOT idle')
                        print('events returned', status_events)
                        
                    self.collectHopperEventsIdle(status_events)
                    self.processHopperEventsIdle()
                else:
                    self.malfunctioned = True
                self.cc2Helper.quiet = False
            
            except:
                self.malfunctioned = True
                print("Unexpected error:", sys.exc_info()[0], logl='error')
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
            
    # this is a 'convenience' function, called during 'get cashbox operation' command after
    # SmartEmpty. If all emptied coins are then reloaded into the Hopper then we can get
    # exact levels of the coins inside.
    # NB this relies on SH3 to return ALL denominations, even with zero levels!
    def initLevels(self, level_data):
        num_denoms = ord(level_data[0])
        denom_rec_size = 9 # 2 level + 4 value + 3 ccode
        
        for rec_no in range(num_denoms):
            denom_rec_data = level_data[1+rec_no*denom_rec_size:1+(rec_no+1)*denom_rec_size]
            denom_emptied = {}
            denom_emptied['lvl'] = struct.unpack('<H', s2b(denom_rec_data[0:2]))[0]
            denom_emptied['val'] = struct.unpack('<I', s2b(denom_rec_data[0:4]))[0]
            denom_emptied['cur'] = denom_rec_data[4:7]
            for i in range(len(self.denoms)):
                denom = self.denoms[i]
                if denom['cur'] == denom_emptied['cur'] and denom['val'] == denom_emptied['val']:
                    denom['lvl'] = denom_emptied['lvl']
                    self.denoms[i] = denom
                    break
            
    def setRoutingAll(self, routing):
        for i in range(len(self.denoms)):
            denom = self.denoms[i]
            denom['rut'] = routing
            self.denoms[i] = denom

    def setRoutingVal(self, routing, value):
        for i in range(len(self.denoms)):
            denom = self.denoms[i]
            if denom['val'] == value:
                denom['rut'] = routing
                self.denoms[i] = denom
                break

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


    def collectHopperEventsCmd(self, status_events):
        for evt in status_events:
            evt_code, evt_data, evt_type = evt
            if evt_code == 0:
                # ignore idle status
                continue
            self.event_list_cmd.append(evt)
        
    def resetHopperEventsCmd(self):
        self.event_list_cmd = []
        self.dispensing = 0
        self.dispensed = 0
        self.failed_payout_amt = 0
        self.failed_payout_evt = 0
        
    def processHopperEventsCmd(self):
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
                self.collectHopperEventsIdle(evt)
            elif evt_code == 12:
                # cashbox paid - not used
                continue
            else:
                print("Unexpected event:", evt, logl='warning')

    def collectHopperEventsIdle(self, status_events):
        '''
        10 : ('Incomplete Payout', 8, 12), 
        13 : ('Coin Credit', 4, 7), 
        16 : ('Fraud Attempt', 4, 8), 
        17 : ('Disabled', 0, 0), 
        19 : ('Slave Reset', 0, 0), 
        54 : ('Multiple Value Added', 4, 8),  
        58 : ('Value Pay-in', 0, 0),  
        '''
        for evt in status_events:
            evt_code, evt_data, evt_type = evt
            if evt_code == 0:
                # ignore idle status
                continue
            self.event_list_idle.append(evt)

    def processHopperEventsIdle(self):
        for evt in self.event_list_idle:
            evt_code, evt_data, evt_type = evt
            if evt_code == 10:
                # incomplete payout
                # fixme action??
                continue
            elif evt_code == 13:
                # Coin Credit
                # todo update levels etc
                continue
            elif evt_code == 16:
                # Fraud Attempt
                # todo action? empty the hopper?
                continue
            elif evt_code == 17:
                # Disabled
                # todo action?
                self.initialised = False
                continue
            elif evt_code == 19:
                # Slave Reset
                # todo reinit hopper?
                self.initialised = False
                continue
            elif evt_code == 54:
                # Multiple Value Added
                continue
            elif evt_code == 58:
                # Value Pay-in
                continue
            else:
                print("Unexpected event:", evt, logl='warning')
                
        self.event_list_idle = []




