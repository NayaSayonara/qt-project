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
from eventdetect import EventDetect
from trackedobject import TrackedObject
from bitmask import BitMask


def card_dispenser_start():
    if pbg.cdInstance is None:
        pbg.cdInstance = CardDispenser()
        pbg.cdInstance.initCd()

def card_dispenser_stop():
    if pbg.cdInstance is not None:
        del pbg.cdInstance
        pbg.cdInstance = None

def dispense_card(timeout=None):
    # debug
    time.sleep(timeout)
    return True
    
    card_dispenser_start()
        
    if pbg.cdInstance.malfunctioned or not pbg.cdInstance.initialised:
        print('card dispenser not working', logl='error')
        return False
        
    if pbg.cdInstance.cdIsHopperEmpty():
        print('card dispenser got no cards', logl='error')
        return False

    dispense_card_timeout_start_time = time.time()
    
    succ, data = pbg.cdInstance.cdDispenseCardOutside()
    if succ and data is not None:
        print('data returned')
        print_hex(data)
    if not succ:
        pbg.cdInstance.malfunctioned = True
        return False
    time.sleep(pbg.cdInstance.min_delay_time)

    while True:
        if timeout is not None:
            if time.time() - dispense_card_timeout_start_time > timeout:
                print('card dispenser timeout on dispense a card', logl='warning')
                return False

        succ, data = pbg.cdInstance.cdCheckCdStatus()
        if succ and data is not None:
            print('data returned')
            print_hex(data)
        if not succ:
            pbg.cdInstance.malfunctioned = True
            return False
            
        if pbg.cdInstance.cdIsDispenseCardError():
            print('card dispenser unable to dispense a card', logl='error')
            return False
        
        if pbg.cdInstance.cdIsDispensingCard():
            time.sleep(pbg.cdInstance.poll_delay_time)
            continue

        #break
        print('dispense card OK')
        return True
    

class CardDispenser:
    
    def __init__(self, serial="/dev/ttyUSB2"):
        self.ev_detect = None
        self.serial_dev = serial
        self.fd_ser = None
        self.EDT = None
        self.ev_q = queue.Queue()
        self.initialised = False
        # global 'working' flag for Card Dispenser
        # misconfiguration, no/bad replies etc - all goes here
        # todo this flag is never reset back to False!
        self.malfunctioned = False
        
        self.cd_cmd_q = queue.Queue()
        self.cd_cmd_rsp_q = queue.Queue()
        self.cd_cmd_current = None
        
        self.min_delay_time = 0.04
        self.poll_delay_time = 0.2
        
        self.dispensing = 0
        self.dispensed = 0
        self.serial_no = 0
        
        self.cd_stat = 0
            
        self.setupComms()
            

    def __del__(self):
        print("CardDispenser instance deleted", threading.current_thread())
        if inspect.currentframe().f_back is not None:
            print("called from ", inspect.currentframe().f_back.f_code.co_name)

        if threading.current_thread() == self.EDT:
            print("CardDispenser is same as event_reader_thread")
        elif self.EDT.is_alive():
            # self.EDT.join(10)
            self.EDT.join()
            print("event_reader_thread joined")
        else:
            print("event_reader_thread dead")
            
        if self.fd_ser is not None:
            self.fd_ser.close()
            self.fd_ser = None


    def setupComms(self):
        try:
            self.fd_ser = serial.Serial(self.serial_dev, 9600, timeout=0.5)
            print("Opened ", self.fd_ser.name)
        except Exception as exc:
            print("Can't open port to Bnv device: %s", exc)
            raise
            
        self.ev_detect = EventDetect(pbg.ev_shutdown, None, self.fd_ser, self.ev_q)
        self.EDT = threading.Thread(target=self.ev_detect.event_reader_thread, args=(), name='CD-ED')
        self.ev_detect.set_ser_readline(False)
        self.EDT.start()
        

    def initCd(self):
        # todo global recovery?
        if self.malfunctioned:
            # disable UI button
            pbg.qt_btn1_state_cd_active.value = False
            self.initialised = False
            return False
            
        if self.initialised:
            return True
            
        # disable UI button
        pbg.qt_btnX_state_cd_active.value = False
        
        succ, data = self.cdRequestSoftwareVersion()
        if succ and data is not None:
            print('data returned')
            print_hex(data)
        if not succ:
            self.malfunctioned = True
            return False
        time.sleep(self.min_delay_time)

        succ, data = self.cdCheckCdStatus()
        if succ and data is not None:
            print('data returned')
            print_hex(data)
        if not succ:
            self.malfunctioned = True
            return False
        time.sleep(self.min_delay_time)
        
        if pbg.cdInstance.cdIsHopperEmpty():
            print('card dispenser got no cards', logl='warning')
            return False
            
        self.initialised = True
        pbg.qt_btn1_state_cd_active.value = True
        
        return True
        

    def cd_single_cmd(self, payload='', timeout=None):
        cd_cmd_timeout = 0.25
        cd_itc_timeout = 0.05
        key = None
        
        cdRequest = self.cdFrameRequest(payload)
        
        request_sent = False
        full_resp_data = bytearray(b'')
        len_full_resp_data = 0
        full_req_data = s2b(cdRequest)
        len_full_req_data = len(full_req_data)
        
        while True:

            if not request_sent:
                cmd_timeout = cd_cmd_timeout
                req_data = full_req_data
            else:
                cmd_timeout = cd_itc_timeout
                req_data = None
                
            rx_data, key, excp = self.ev_detect.x_ser(tx_data=req_data, x_ser_timeout=cmd_timeout)
                
            if key is not None:
                raise CustomException('key exception support is missing')
                return False, None, key

            if excp is not None and excp != queue.Empty:
                print("cd_single_cmd exception ", excp)
                return False, None, key
                
            if excp == queue.Empty:
                if len_full_resp_data > 0:
                    succ, rsp_payload = self.cdUnframeResponse(bytes(full_resp_data))
                    if succ:
                        return True, rsp_payload, key
                    else:
                        print("cd_single_cmd unframing failed")
                        print_hex(bytes(full_resp_data))
                        return False, None, key
                else:
                    print("cd_single_cmd timeout ")
                    return False, None, key

            if rx_data is not None and len(rx_data) > 0:
                if not request_sent:
                    #print('read', rx_data.hex())
                    #print('timeout was', cmd_timeout)
                    pass
                else:
                    #print('read more', rx_data.hex())
                    #print('timeout was', cmd_timeout)
                    pass
                full_resp_data.extend(rx_data)
                len_full_resp_data = len(full_resp_data)
            else:
                print('read nothing, timeout was', cmd_timeout)

            request_sent = True


    def cdFrameRequest(self, payload):
        # big endian for MT166
        frame_len = struct.pack('>H', len(payload))
        frame = pbg.cdSTX + frame_len + s2b(payload) + pbg.cdETX
        bcc = calcBCC(frame)
        frame += struct.pack('B', bcc)
        return frame
        

    def cdUnframeResponse(self, frame):
        # todo trim frame first to STX-ETX content?
        if frame[0] != pbg.cdSTX or frame[-2] != pbg.cdETX:
            print('Invalid frame', logl='warning')
            print_hex(frame)
            return False, ''
        bcc = calcBCC(frame[0:-1])
        if bcc != frame[-1]:
            print('Invalid checksum', bcc, frame[-1], logl='warning')
            print_hex(frame)
            return False, ''

        # big endian for MT166
        frame_len = struct.unpack('>H', frame[1:3])[0]
        if frame_len != len(frame[3:-2]):
            print('Invalid frame length', frame_len, len(frame[3:-2]), logl='warning')
            print_hex(frame)
            return False, ''

        return b2s(frame[3:-2])


    def calcBCC(self, data):
        cs = 0
        for byte in data:
            if type(byte) is str:
                cs = cs ^ ord(byte)
            else:
                cs = cs ^ byte
        return cs
        

    def cdRequestSoftwareVersion(self):
        for _ in range(pbg.cd_cmd_retries):
            payload = '00'
            
            succ, rx_data, key = self.cc2_single_cmd(payload=payload)
            if not succ:
                print('no response on cmd', payload)
                time.sleep(pbg.cd_cmd_retry_delay)
                continue
        
            else:
                print("Response: ")
                print_hex(rx_data)
                if rx_data[2] == pbg.cdOK:
                    return True, rx_data
                else:
                    return False, rx_data
        return False, None


    def cdDispenseCardOutside(self):
        for _ in range(pbg.cd_cmd_retries):
            payload = '12'
            
            succ, rx_data, key = self.cc2_single_cmd(payload=payload)
            if not succ:
                print('no response on cmd', payload)
                time.sleep(pbg.cd_cmd_retry_delay)
                continue
        
            else:
                print("Response: ")
                print_hex(rx_data)
                if rx_data[2] == pbg.cdOK:
                    return True, rx_data
                else:
                    return False, rx_data
        return False, None


    def cdCheckCdStatus(self):
        for _ in range(pbg.cd_cmd_retries):
            payload = '20'
            
            succ, rx_data, key = self.cc2_single_cmd(payload=payload)
            if not succ:
                print('no response on cmd', payload)
                time.sleep(pbg.cd_cmd_retry_delay)
                continue
        
            else:
                print("Response: ")
                print_hex(rx_data)
                
                if rx_data[2] == pbg.cdOK:
                    self.cd_stat = ord(rx_data[2])
                    return True, rx_data
                else:
                    return False, rx_data
                
        return False, None


    def cdIsHopperEmpty(self):
        return bool(self.cd_stat & BitMask.B7)

    def cdIsDispensingCard(self):
        return bool(self.cd_stat & BitMask.B3)

    def cdIsDispenseCardError(self):
        return bool(self.cd_stat & BitMask.B1)


