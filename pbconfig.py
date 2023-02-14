import configparser
import time

import pbglobals as pbg
from utils import *
import ursula
import ecr


class PBConfig:

    def __init__(self, ini_file_name=''):
        if ini_file_name == '':
            self._ini_file_name = pbg.ini_file_name_default
        else:
            self._ini_file_name = ini_file_name
            
        self._ini_file_cfg = configparser.ConfigParser()

        self._serial_prefix = "/dev/"
        self._gHOPPER_SERIAL_DEVICE = "ttyUSBhopper"
        self._gHOPPER_SERIAL_DEVICE_FULL = self._serial_prefix + self._gHOPPER_SERIAL_DEVICE
        self._gBNV_SERIAL_DEVICE = "ttyUSBbnv"
        self._gBNV_SERIAL_DEVICE_FULL = self._serial_prefix + self._gBNV_SERIAL_DEVICE
        self._gNFC_SERIAL_DEVICE = "ttyUSBnfc"
        self._gNFC_SERIAL_DEVICE_FULL = self._serial_prefix + self._gNFC_SERIAL_DEVICE
        self._gCD_SERIAL_DEVICE = "ttyUSBcd"
        self._gCD_SERIAL_DEVICE_FULL = self._serial_prefix + self._gCD_SERIAL_DEVICE
        
    @property
    def gHOPPER_SERIAL_DEVICE(self):
        return self._gHOPPER_SERIAL_DEVICE_FULL

    @gHOPPER_SERIAL_DEVICE.setter
    def gHOPPER_SERIAL_DEVICE(self, value):
        self._gHOPPER_SERIAL_DEVICE = value
        self._gHOPPER_SERIAL_DEVICE_FULL = self._serial_prefix + self._gHOPPER_SERIAL_DEVICE

    @property
    def gBNV_SERIAL_DEVICE(self):
        return self._gBNV_SERIAL_DEVICE_FULL

    @gBNV_SERIAL_DEVICE.setter
    def gBNV_SERIAL_DEVICE(self, value):
        self._gBNV_SERIAL_DEVICE = value
        self._gBNV_SERIAL_DEVICE_FULL = self._serial_prefix + self._gBNV_SERIAL_DEVICE

    @property
    def gNFC_SERIAL_DEVICE(self):
        return self._gNFC_SERIAL_DEVICE_FULL

    @gNFC_SERIAL_DEVICE.setter
    def gNFC_SERIAL_DEVICE(self, value):
        self._gNFC_SERIAL_DEVICE = value
        self._gNFC_SERIAL_DEVICE_FULL = self._serial_prefix + self._gNFC_SERIAL_DEVICE

    @property
    def gCD_SERIAL_DEVICE(self):
        return self._gCD_SERIAL_DEVICE_FULL

    @gCD_SERIAL_DEVICE.setter
    def gCD_SERIAL_DEVICE(self, value):
        self._gCD_SERIAL_DEVICE = value
        self._gCD_SERIAL_DEVICE_FULL = self._serial_prefix + self._gCD_SERIAL_DEVICE


    def readConfig(self):
        self._ini_file_cfg.read(self._ini_file_name)
        if not self._ini_file_cfg.sections():
            print("Empty or no .ini file supplied at ", self._ini_file_name)
        else:
            print("Found .ini file supplied at ", self._ini_file_name)
            section = 'All'
            if section in self._ini_file_cfg:

                ini_key = 'POS.Link.Up.Timeout'
                ini_val = self._ini_file_cfg.getfloat(section, ini_key, fallback=ecr.gpLINKUP_TO)
                ecr.gpLINKUP_TO = ini_val
                print("ini key %s (section %s) value is " % (ini_key, section), ini_val)

                ini_key = 'POS.Response.Timeout'
                ini_val = self._ini_file_cfg.getfloat(section, ini_key, fallback=ecr.gpRSP_TO)
                ecr.gpRSP_TO = ini_val
                print("ini key %s (section %s) value is " % (ini_key, section), ini_val)

                ini_key = 'Journal.Data.Path'
                ini_val = self._ini_file_cfg.get(section, ini_key, fallback=ursula.JRN_DATA_PATH)
                ursula.JRN_DATA_PATH = ini_val
                print("ini key %s (section %s) value is " % (ini_key, section), ini_val)

                ini_key = 'Ursula.URL'
                ini_val = self._ini_file_cfg.get(section, ini_key, fallback=ursula.URSULA_URL)
                ursula.URSULA_URL = ini_val
                print("ini key %s (section %s) value is " % (ini_key, section), ini_val)
                
                ini_key = 'Ursula.TID.CUG'
                ini_val = self._ini_file_cfg.get(section, ini_key, fallback=ursula.URSULA_TID_CUG)
                ursula.URSULA_TID_CUG = ini_val
                print("ini key %s (section %s) value is " % (ini_key, section), ini_val)
                
                ini_key = 'Hopper.Serial.Device'
                ini_val = self._ini_file_cfg.get(section, ini_key, fallback=self._gHOPPER_SERIAL_DEVICE)
                self.gHOPPER_SERIAL_DEVICE = ini_val
                print("ini key %s (section %s) value is " % (ini_key, section), ini_val)
                
                ini_key = 'BNV.Serial.Device'
                ini_val = self._ini_file_cfg.get(section, ini_key, fallback=self._gBNV_SERIAL_DEVICE)
                self.gBNV_SERIAL_DEVICE = ini_val
                print("ini key %s (section %s) value is " % (ini_key, section), ini_val)
                
                ini_key = 'NFC.Serial.Device'
                ini_val = self._ini_file_cfg.get(section, ini_key, fallback=self._gNFC_SERIAL_DEVICE)
                self.gNFC_SERIAL_DEVICE = ini_val
                print("ini key %s (section %s) value is " % (ini_key, section), ini_val)
                
                ini_key = 'CD.Serial.Device'
                ini_val = self._ini_file_cfg.get(section, ini_key, fallback=self._gCD_SERIAL_DEVICE)
                self.gCD_SERIAL_DEVICE = ini_val
                print("ini key %s (section %s) value is " % (ini_key, section), ini_val)
                

    def saveConfig(self, section, ini_key, value):
        #section = 'All'
        #ini_key = 'Ursula.URL'
        if section not in self._ini_file_cfg:
            self._ini_file_cfg[section] = {}
            
        if type(value) is str:
            self._ini_file_cfg[section][ini_key] = value
        else:
            self._ini_file_cfg[section][ini_key] = str(value)
        
        with open(self._ini_file_name, 'w') as inifile:
            self._ini_file_cfg.write(inifile)
            print("Saved updated .ini file supplied at ", self._ini_file_name)


