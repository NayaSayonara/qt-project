from logprint import print

import pynfc
import ctypes
from ctypes import pointer, byref, c_ubyte, cast, c_char_p
import os
#import datetime
from datetime import datetime
import time

from pbce import CustomException
import pbglobals as pbg
from utils import *

MIFARE_KEY_TYPE = ctypes.c_ubyte * 6
#MIFARE_KEYA = MIFARE_KEY_TYPE(0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF)
MIFARE_KEYA = [
MIFARE_KEY_TYPE(0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5),
MIFARE_KEY_TYPE(0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5),
MIFARE_KEY_TYPE(0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5),
MIFARE_KEY_TYPE(0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5),

MIFARE_KEY_TYPE(0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5),
MIFARE_KEY_TYPE(0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5),
MIFARE_KEY_TYPE(0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5),
MIFARE_KEY_TYPE(0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5),

MIFARE_KEY_TYPE(0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5),
MIFARE_KEY_TYPE(0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5),
MIFARE_KEY_TYPE(0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5),
MIFARE_KEY_TYPE(0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5),

MIFARE_KEY_TYPE(0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5),
MIFARE_KEY_TYPE(0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5),
MIFARE_KEY_TYPE(0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5),
MIFARE_KEY_TYPE(0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5)
]

MIFARE_KEYB = MIFARE_KEY_TYPE(0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF)

class VtekNfc:
    
    #def __init__(self, serial="pn532_spi:/dev/spidev0.0:275000"):
    #def __init__(self, serial="pn532_uart:/dev/ttyUSB1:115200"):
    def __init__(self, serial="/dev/ttyUSB1"):
    
        self.serial_dev = 'pn532_uart:' + serial + ':115200'
        
        self.pan1=""
        self.pan2=""
        self.uid=""
        
        self.pctx = None
        self.pdevice = None

        self.ptarget = None
        
        self.log_level = None

        if self.log_level is not None:
            os.environ["LIBNFC_LOG_LEVEL"] = str(log_level)
        if self.serial_dev is not None:
            os.environ["LIBNFC_DEFAULT_DEVICE"] = self.serial_dev
        
        self.getVersion()

        self.pctx = ctypes.POINTER(pynfc.nfc.struct_nfc_context)()
        pynfc.nfc.nfc_init(self.pctx) #Mallocs the ctx
        if not self.pctx:
            raise Exception("Couldn't nfc_init (malloc?)")

        print('opening nfc device at', self.serial_dev)

        pynfc.nfc.nfc_open.argtypes = [ctypes.POINTER(pynfc.nfc.struct_nfc_context), ctypes.POINTER(ctypes.c_char)]
        self.pdevice = pynfc.nfc.nfc_open(self.pctx, None)
        if not self.pdevice:
            raise CustomException("Couldn't nfc_open (comms?)")

        self.modulations=((pynfc.nfc.NMT_ISO14443A, pynfc.nfc.NBR_106),)
        # number of polling (0x01 – 0xFE: 1 up to 254 polling, 0xFF: Endless polling)
        self.times=0xFF
        # polling period in units of 150 ms (0x01 – 0x0F: 150ms – 2.25s)
        self.delay=1

    def __del__(self):
        #print("Cleanup and exit..")
        if self.pdevice:
            pynfc.nfc.nfc_close(self.pdevice)
        pynfc.nfc.nfc_exit(self.pctx)

    def getVersion(self):
        ver_string = ctypes.string_at(pynfc.nfc.nfc_version()).decode("utf-8")
        print('nfc lib version', ver_string)
        return ver_string

    def removeCard(self, timeout=None):
        print("Please remove Tag")
        while (0 == pynfc.nfc.nfc_initiator_target_is_present(self.pdevice, None)):
            time.sleep(0.2)

    def readCard(self, timeout=None):
        print("Please present Tag")
        if timeout is not None:
            # delay 1 yields max of 254*0.15 = 38.1 seconds
            # so use delay=1 if timeout<38 and delay=2 if 38<timeout<38*2
            if timeout < 38:
                self.times=int(timeout//0.15)
                self.delay=1
            elif timeout < 38*2:
                self.times=int(timeout//0.15)
                self.delay=2
        else:
            self.times=0xFF
            self.delay=1
        
        _modulations = (
            pynfc.nfc.nfc_modulation * len(self.modulations)
        )()
        for i, (nmt, nbr) in enumerate(self.modulations):
            _modulations[i].nmt = nmt
            _modulations[i].nbr = nbr
        target = pynfc.nfc.nfc_target()
        while True:
            #numdev = pynfc.nfc.nfc_initiator_poll_target(
            numdev = pynfc.poll(
                self.pdevice,
                _modulations,
                len(_modulations),
                self.times,
                self.delay,
                target
            )
            if numdev <= 0:
                print("nfc poll error ", numdev)
                return False, None, None
                #break
                
            print("nfc poll targets found: ", numdev)
            self.ptarget = pynfc.tag_new(self.pdevice, target.nti.nai)
            
            if not self.ptarget:
                # todo use case? Timeout is messed up probably...
                continue
                
            this_target = pynfc.Target(self.ptarget)
            if this_target.type == pynfc.nfc.DESFIRE:
                print("Desfire Tag found")
                #this_target = pynfc.Desfire(self.ptarget)
                pynfc.nfc.freefare_free_tag(self.ptarget)
                return False, None, None
                #continue
                
            elif this_target.type == pynfc.nfc.CLASSIC_1K or this_target.type == pynfc.nfc.CLASSIC_4K:
                print("Mifare Classic 1k/4k Tag found")
                this_target = pynfc.Mifare(self.ptarget)
                #print(this_target.uid)
                self.uid = ctypes.string_at(this_target.uid).decode("utf-8")
                
                print(ctypes.string_at(pynfc.nfc.freefare_get_tag_friendly_name(self.ptarget)).decode("utf-8"))
                
                if pynfc.nfc.mifare_classic_connect(self.ptarget) != 0:
                    print("classic_connect error")
                    break
                    
                t00 = datetime.now()
                #sector=1
                #for sector in range(0, 16):
                for sector in range(1, 2):
                    akey=True
                    print("Authenticating sector ", sector)
                    t0 = datetime.now()
                    block = pynfc.nfc.mifare_classic_sector_last_block(sector)
                    #auth_tag = nfc.mifare_classic_tag.from_buffer_copy(data)
                    this_key = MIFARE_KEYA[sector]
                    if akey:
                        ret = pynfc.nfc.mifare_classic_authenticate(
                            self.ptarget,
                            block,
                            this_key,
                            pynfc.nfc.MFC_KEY_A
                        )
                    else:
                        ret = pynfc.nfc.mifare_classic_authenticate(
                            self.ptarget,
                            block,
                            MIFARE_KEYB,
                            pynfc.nfc.MFC_KEY_B
                        )
                    t1 = datetime.now()
                    if ret == 0:
                        print("auth success")
                        pass
                    else:
                        print("auth FAILURE", logl='warning')
                        pynfc.nfc.freefare_free_tag(self.ptarget)
                        return False, None, None
                        #break
                        
                    read_data = pynfc.nfc.MifareClassicBlock()
                    read_block = pynfc.nfc.mifare_classic_sector_first_block(sector)
    
                    t2 = datetime.now()
                    pynfc.nfc.mifare_classic_read(self.ptarget, read_block, pointer(read_data))
                    print_hex(read_data, 16)
                    if sector == 1:
                        szBytes = 6
                        pbtData = read_data
                        pan2f = str("".join(["{0:02x}".format(pbtData[szPos]) for szPos in range(szBytes)]))
                        self.pan2 = pan2f[:-1]
                        #print(self.pan2)
                    
                    t3 = datetime.now()
                    read_block += 1
                    pynfc.nfc.mifare_classic_read(self.ptarget, read_block, pointer(read_data))
                    print_hex(read_data, 16)
                    if sector == 1:
                        szBytes = 4
                        pbtData = read_data
                        self.pan1 = str("".join(["{0:02x}".format(pbtData[szPos]) for szPos in range(szBytes)]))
                        #print(self.pan1)
                    '''
                    t4 = datetime.now()
                    read_block += 1
                    pynfc.nfc.mifare_classic_read(self.ptarget, read_block, pointer(read_data))
                    print_hex(read_data, 16)
                    
                    t5 = datetime.now()
                    read_block += 1
                    pynfc.nfc.mifare_classic_read(self.ptarget, read_block, pointer(read_data))
                    print_hex(read_data, 16)
                    
                    t6 = datetime.now()
                    '''
                    '''
                    print("Timings:")
                    print("Auth: ", t1-t0)
                    print("Blk0: ", t3-t2)
                    print("Blk1: ", t4-t3)
                    print("Blk2: ", t5-t4)
                    print("Blk3: ", t6-t5)
                    
                    print("Blk0-3: ", t6-t2)
                    print("All: ", t1-t0 + t6-t2)
                    '''
                break
            else:
                print("Other Tag found", this_target.type )
                pynfc.nfc.freefare_free_tag(self.ptarget)
                return False, None, None
                #continue
        '''
        t01 = datetime.now()
        print("Global Timings:")
        # 670-750ms for 16 sectors of 1k Classic
        print("All sectors auth and read: ", t01-t00)
        '''
        print("Card UID is ", self.uid)
        print("Card Serial is ", self.pan2)
        print("Full PAN is ", self.pan1+self.pan2)
        
        pynfc.nfc.freefare_free_tag(self.ptarget)

        return True, self.pan1+self.pan2, self.uid



