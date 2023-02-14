from logprint import print

import time
import struct
import queue

#import pbglobals as pbg
from pbce import CustomException
from utils import *
from cc2 import *
from bitmask import BitMask
from billstatus import BillStatus


class Cc2Helper:
    
    def __init__(self, parent_device=None, event_manager=None, cc2echo=False):
        self._parentDeviceObj = parent_device
        self._evtMgr = event_manager
        self._cc2echo = cc2echo
        self.quiet = False
        self._cc2Addr = 0
        
    def set_parentDeviceObj(self, parent_device):
        self._parentDeviceObj = parent_device
        if self._cc2Addr == 0:
            self._cc2Addr = self._parentDeviceObj.getCc2Addr()
        else:
            raise CustomException('cc2 address is already set')
    
    def get_parentDeviceObj(self):
        return self._parentDeviceObj
    
    def cc2_single_cmd(self, header=0, payload='', timeout=None):
        cc2_cmd_timeout = 0.25
        cc2_itc_timeout = 0.05
        key = None
        
        # payload = tx_data
        #cc2request = ccTalkMessage(source=1, destination=self._cc2Addr, header=header, payload=payload)
        cc2request = ccTalkMessage(source=1, destination=self._parentDeviceObj.getCc2Addr(), header=header, payload=payload)
        if not self.quiet:
            print("Request: ", cc2request.payload.headerType)
            #print(s2b(cc2request.raw()).hex())
            print_hex(cc2request.raw())
            #print_dec(cc2request.raw())
        
        # first response bytes should appear within cc2_cmd_timeout or return timeout
        # then assume a complete response set if no additional bytes received within cc2_itc_timeout
        
        # for echo mode we have 3 stages:
        # 1 - from 1 to full_req_data bytes received - use cc2_itc_timeout or shorter (data pre-available)
        # 2 - full_req_data bytes received; nothing else can be available until cc2_cmd_timeout
        # 3 - from 1 to full_resp_data received - use cc2_itc_timeout
        
        request_sent = False
        full_resp_data = bytearray(b'')
        len_full_resp_data = 0
        full_req_data = s2b(cc2request.raw())
        len_full_req_data = len(full_req_data)
        
        while True:

            if not request_sent:
                # stage 1 - first request
                if self._cc2echo:
                    cmd_timeout = cc2_itc_timeout
                else:
                    cmd_timeout = cc2_cmd_timeout
                req_data = full_req_data
            else:
                # stages 2 and 3
                if self._cc2echo:
                    if len_full_resp_data < len_full_req_data:
                        cmd_timeout = cc2_itc_timeout
                    elif len_full_resp_data == len_full_req_data:
                        cmd_timeout = cc2_cmd_timeout
                        #print('full timeout set (echo)')
                    else:
                        cmd_timeout = cc2_itc_timeout
                else:
                    cmd_timeout = cc2_itc_timeout
                req_data = None
                
            rx_data, key, excp = self._evtMgr.x_ser(tx_data=req_data, x_ser_timeout=cmd_timeout)
                
            if key is not None:
                raise CustomException('key exception support is missing')
                return False, None, key

            if excp is not None and excp != queue.Empty:
                print("cc2_single_cmd exception ", excp)
                return False, None, key
                
            if excp == queue.Empty:
                if self._cc2echo:
                    if len_full_resp_data > len_full_req_data:
                        # verify first part of full_resp_data is actually
                        # full_req_data, remove echo bytes and return the rest
                        pref, echo, suf = full_resp_data.partition(full_req_data)
                        if len(pref) > 0:
                            print("unexpected bytes before echo request", pref, logl='warning')
                        if len(suf) == 0:
                            print("response data missing in", full_resp_data, logl='warning')
                        #return True, bytes(full_resp_data), key
                        return True, bytes(suf), key
                    else:
                        print("cc2_single_cmd timeout (echo) ")
                        return False, None, key
                else:
                    if len_full_resp_data > 0:
                        return True, bytes(full_resp_data), key
                    else:
                        print("cc2_single_cmd timeout ")
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


    def cc2Poll(self):
        # simple poll
        for _ in range(pbg.cc2_cmd_retries):
            cc2_cmd = 254
            succ, rx_data, key = self.cc2_single_cmd(header=cc2_cmd)
            if not succ:
                print('no response on cmd', cc2_cmd)
                time.sleep(pbg.cc2_cmd_retry_delay)
                continue
            else:
                cc2response = ccTalkMessage(data=b2s(rx_data))
                print("Response: ", cc2response.payload.headerType)

                if cc2response.payload.header == 6:
                    # Busy
                    print('Busy response on cmd', cc2_cmd)
                    time.sleep(pbg.cc2_cmd_retry_delay)
                    continue
                if cc2response.payload.header == 5:
                    # NAK
                    print('NAK response on cmd', cc2_cmd)
                    #raise CustomException('NAK response on cmd')
                    break
                    
                return True
        return False

    def cc2SmartEmpty(self):
        # smart empty
        for _ in range(pbg.cc2_cmd_retries):
            cc2_cmd = 51
            succ, rx_data, key = self.cc2_single_cmd(header=cc2_cmd)
            if not succ:
                print('no response on cmd', cc2_cmd)
                time.sleep(pbg.cc2_cmd_retry_delay)
                continue
            else:
                cc2response = ccTalkMessage(data=b2s(rx_data))
                print("Response: ", cc2response.payload.headerType)
                print_hex(cc2response.raw())

                if cc2response.payload.header == 6:
                    # Busy
                    print('Busy response on cmd', cc2_cmd)
                    time.sleep(pbg.cc2_cmd_retry_delay)
                    continue
                if cc2response.payload.header == 5:
                    # NAK
                    print('NAK response on cmd', cc2_cmd)
                    #raise CustomException('NAK response on cmd')
                    break

                payload = cc2response.getPayload()
                cc2response.payload.parsePayload(header=cc2_cmd)
                return True, payload[1:]
        return False, None

    def cc2GetPayoutOptions(self):
        # Get Payout Options
        for _ in range(pbg.cc2_cmd_retries):
            cc2_cmd = 31
            succ, rx_data, key = self.cc2_single_cmd(header=cc2_cmd)
            if not succ:
                print('no response on cmd', cc2_cmd)
                time.sleep(pbg.cc2_cmd_retry_delay)
                continue
            else:
                cc2response = ccTalkMessage(data=b2s(rx_data))
                print("Response: ", cc2response.payload.headerType)
                print_hex(cc2response.raw())

                if cc2response.payload.header == 6:
                    # Busy
                    print('Busy response on cmd', cc2_cmd)
                    time.sleep(pbg.cc2_cmd_retry_delay)
                    continue
                if cc2response.payload.header == 5:
                    # NAK
                    print('NAK response on cmd', cc2_cmd)
                    #raise CustomException('NAK response on cmd')
                    break

                payload = cc2response.getPayload()
                cc2response.payload.parsePayload(header=cc2_cmd)
                return True, payload[1:]
        return False, None

    def cc2SetPayoutOptions(self, opt1, opt2):
        # Set Payout Options
        for _ in range(pbg.cc2_cmd_retries):
            cc2_cmd = 30
            payload = b2s(struct.pack('BB', opt1, opt2))
            succ, rx_data, key = self.cc2_single_cmd(header=cc2_cmd, payload=payload)
            if not succ:
                print('no response on cmd', cc2_cmd)
                time.sleep(pbg.cc2_cmd_retry_delay)
                continue
            else:
                cc2response = ccTalkMessage(data=b2s(rx_data))
                print("Response: ", cc2response.payload.headerType)
                print_hex(cc2response.raw())

                if cc2response.payload.header == 6:
                    # Busy
                    print('Busy response on cmd', cc2_cmd)
                    time.sleep(pbg.cc2_cmd_retry_delay)
                    continue
                if cc2response.payload.header == 5:
                    # NAK
                    print('NAK response on cmd', cc2_cmd)
                    #raise CustomException('NAK response on cmd')
                    break

                payload = cc2response.getPayload()
                cc2response.payload.parsePayload(header=cc2_cmd)
                return True, payload[1:]
        return False, None

    def cc2RequestEncryptionSupport(self):
        # request encryption support
        for _ in range(pbg.cc2_cmd_retries):
            cc2_cmd = 111
            succ, rx_data, key = self.cc2_single_cmd(header=cc2_cmd, payload='\xAA\x55\x00\x00\x55\xAA')
            if not succ:
                print('no response on cmd', cc2_cmd)
                time.sleep(pbg.cc2_cmd_retry_delay)
                continue
            else:
                cc2response = ccTalkMessage(data=b2s(rx_data))
                print("Response: ", cc2response.payload.headerType)
                print_hex(cc2response.raw())

                if cc2response.payload.header == 6:
                    # Busy
                    print('Busy response on cmd', cc2_cmd)
                    time.sleep(pbg.cc2_cmd_retry_delay)
                    continue
                if cc2response.payload.header == 5:
                    # NAK
                    print('NAK response on cmd', cc2_cmd)
                    #raise CustomException('NAK response on cmd')
                    break

                payload = cc2response.getPayload()
                return True, payload[1:]
        return False, None

    def cc2SetMasterInhibitStatus(self, enabled=True):
        # Set Master Inhibit Status
        for _ in range(pbg.cc2_cmd_retries):
            cc2_cmd = 228
            if enabled:
                payload='\x01'
            else:
                payload='\x00'
            succ, rx_data, key = self.cc2_single_cmd(header=cc2_cmd, payload=payload)
            if not succ:
                print('no response on cmd', cc2_cmd)
                time.sleep(pbg.cc2_cmd_retry_delay)
                continue
            else:
                cc2response = ccTalkMessage(data=b2s(rx_data))
                print("Response: ", cc2response.payload.headerType)
                print_hex(cc2response.raw())

                if cc2response.payload.header == 6:
                    # Busy
                    print('Busy response on cmd', cc2_cmd)
                    time.sleep(pbg.cc2_cmd_retry_delay)
                    continue
                if cc2response.payload.header == 5:
                    # NAK
                    print('NAK response on cmd', cc2_cmd)
                    #raise CustomException('NAK response on cmd')
                    break

                payload = cc2response.getPayload()
                return True, payload[1:]
        return False, None
                
    def cc2GetMasterInhibitStatus(self):
        # Get Master Inhibit Status
        for _ in range(pbg.cc2_cmd_retries):
            cc2_cmd = 227
            succ, rx_data, key = self.cc2_single_cmd(header=cc2_cmd)
            if not succ:
                print('no response on cmd', cc2_cmd)
                time.sleep(pbg.cc2_cmd_retry_delay)
                continue
            else:
                cc2response = ccTalkMessage(data=b2s(rx_data))
                print("Response: ", cc2response.payload.headerType)
                print_hex(cc2response.raw())

                if cc2response.payload.header == 6:
                    # Busy
                    print('Busy response on cmd', cc2_cmd)
                    time.sleep(pbg.cc2_cmd_retry_delay)
                    continue
                if cc2response.payload.header == 5:
                    # NAK
                    print('NAK response on cmd', cc2_cmd)
                    #raise CustomException('NAK response on cmd')
                    break

                payload = cc2response.getPayload()
                return True, payload[1:]
        return False, None


    def cc2ResetDevice(self):
        # Reset device
        for _ in range(pbg.cc2_cmd_retries):
            cc2_cmd = 1
            succ, rx_data, key = self.cc2_single_cmd(header=cc2_cmd)
            if not succ:
                print('no response on cmd', cc2_cmd)
                time.sleep(pbg.cc2_cmd_retry_delay)
                continue
            else:
                cc2response = ccTalkMessage(data=b2s(rx_data))
                print("Response: ", cc2response.payload.headerType)
                print_hex(cc2response.raw())

                if cc2response.payload.header == 6:
                    # Busy
                    print('Busy response on cmd', cc2_cmd)
                    time.sleep(pbg.cc2_cmd_retry_delay)
                    continue
                if cc2response.payload.header == 5:
                    # NAK
                    print('NAK response on cmd', cc2_cmd)
                    #raise CustomException('NAK response on cmd')
                    break

                payload = cc2response.getPayload()
                return True, payload[1:]
        return False, None


    def cc2RequestSoftwareRevision(self):
        # Request software revision
        for _ in range(pbg.cc2_cmd_retries):
            cc2_cmd = 241
            succ, rx_data, key = self.cc2_single_cmd(header=cc2_cmd)
            if not succ:
                print('no response on cmd', cc2_cmd)
                time.sleep(pbg.cc2_cmd_retry_delay)
                continue
            else:
                cc2response = ccTalkMessage(data=b2s(rx_data))
                print("Response: ", cc2response.payload.headerType)
                print_hex(cc2response.raw())

                if cc2response.payload.header == 6:
                    # Busy
                    print('Busy response on cmd', cc2_cmd)
                    time.sleep(pbg.cc2_cmd_retry_delay)
                    continue
                if cc2response.payload.header == 5:
                    # NAK
                    print('NAK response on cmd', cc2_cmd)
                    #raise CustomException('NAK response on cmd')
                    break

                payload = cc2response.getPayload()
                return True, payload[1:]
        return False, None


    def cc2RequestSerialNumber(self):
        # Request serial number
        for _ in range(pbg.cc2_cmd_retries):
            cc2_cmd = 242
            succ, rx_data, key = self.cc2_single_cmd(header=cc2_cmd)
            if not succ:
                print('no response on cmd', cc2_cmd)
                time.sleep(pbg.cc2_cmd_retry_delay)
                continue
            else:
                cc2response = ccTalkMessage(data=b2s(rx_data))
                print("Response: ", cc2response.payload.headerType)
                print_hex(cc2response.raw())

                if cc2response.payload.header == 6:
                    # Busy
                    print('Busy response on cmd', cc2_cmd)
                    time.sleep(pbg.cc2_cmd_retry_delay)
                    continue
                if cc2response.payload.header == 5:
                    # NAK
                    print('NAK response on cmd', cc2_cmd)
                    #raise CustomException('NAK response on cmd')
                    break

                payload = cc2response.getPayload()
                if self._parentDeviceObj is not None:
                    self._parentDeviceObj.setSerialNumber(payload[1:])
                return True, payload[1:]
        return False, None


    def cc2RequestCountryScalingFactor(self):
        # Request country scaling factor
        for _ in range(pbg.cc2_cmd_retries):
            cc2_cmd = 156

            payload = ''
            if self._parentDeviceObj is not None:
                payload = self._parentDeviceObj.country
            else:
                raise CustomException('need parent object to get country code')
            
            succ, rx_data, key = self.cc2_single_cmd(header=cc2_cmd, payload=payload)
            if not succ:
                print('no response on cmd', cc2_cmd)
                time.sleep(pbg.cc2_cmd_retry_delay)
                continue
            else:
                cc2response = ccTalkMessage(data=b2s(rx_data))
                print("Response: ", cc2response.payload.headerType)
                print_hex(cc2response.raw())

                if cc2response.payload.header == 6:
                    # Busy
                    print('Busy response on cmd', cc2_cmd)
                    time.sleep(pbg.cc2_cmd_retry_delay)
                    continue
                if cc2response.payload.header == 5:
                    # NAK
                    print('NAK response on cmd', cc2_cmd)
                    #raise CustomException('NAK response on cmd')
                    break

                payload = cc2response.getPayload()
                if self._parentDeviceObj is not None:
                    scaling_factor = ord(payload[1]) + 256 * ord(payload[2])
                    self._parentDeviceObj.setScalingFactor(scaling_factor)
                return True, payload[1:]
        return False, None


    def cc2RequestBillId(self, bill_id):
        # Request bill id
        for _ in range(pbg.cc2_cmd_retries):
            cc2_cmd = 157

            payload = b2s(struct.pack('<B', bill_id))
            
            succ, rx_data, key = self.cc2_single_cmd(header=cc2_cmd, payload=payload)
            if not succ:
                print('no response on cmd', cc2_cmd)
                time.sleep(pbg.cc2_cmd_retry_delay)
                continue
            else:
                cc2response = ccTalkMessage(data=b2s(rx_data))
                print("Response: ", cc2response.payload.headerType)
                print_hex(cc2response.raw())

                if cc2response.payload.header == 6:
                    # Busy
                    print('Busy response on cmd', cc2_cmd)
                    time.sleep(pbg.cc2_cmd_retry_delay)
                    continue
                if cc2response.payload.header == 5:
                    # NAK
                    print('NAK response on cmd', cc2_cmd)
                    #raise CustomException('NAK response on cmd')
                    break

                payload = cc2response.getPayload()
                if self._parentDeviceObj is not None:
                    self._parentDeviceObj.setBillId(bill_id, payload[1:])
                return True, payload[1:]
        return False, None


    def cc2RouteBill(self, return_bill=False):
        # Route bill
        for _ in range(pbg.cc2_cmd_retries):
            cc2_cmd = 154
            
            if return_bill:
                route_code = 0
            else:
                # send to cashbox/recycler
                route_code = 1
            
            payload = b2s(struct.pack('<B', route_code))
            
            succ, rx_data, key = self.cc2_single_cmd(header=cc2_cmd, payload=payload)
            if not succ:
                print('no response on cmd', cc2_cmd)
                time.sleep(pbg.cc2_cmd_retry_delay)
                continue
            else:
                cc2response = ccTalkMessage(data=b2s(rx_data))
                print("Response: ", cc2response.payload.headerType)
                print_hex(cc2response.raw())

                if cc2response.payload.header == 6:
                    # Busy
                    print('Busy response on cmd', cc2_cmd)
                    time.sleep(pbg.cc2_cmd_retry_delay)
                    continue
                if cc2response.payload.header == 5:
                    # NAK
                    print('NAK response on cmd', cc2_cmd)
                    #raise CustomException('NAK response on cmd')
                    break

                payload = cc2response.getPayload()
                if self._parentDeviceObj is not None:
                    if cc2response.payload.header != 0:
                        # route bill failed
                        print('route bill failed', cc2response.payload.header, logl='warning')
                        self._parentDeviceObj.current_bill_status = BillStatus.IN_ESCROW
                    else:
                        # todo actual status will be in the next events??
                        if return_bill:
                            self._parentDeviceObj.current_bill_status = BillStatus.ROUTING_OUT
                        else:
                            self._parentDeviceObj.current_bill_status = BillStatus.ROUTING_IN
                else:
                    raise CustomException('need parent object to route bills')
                return True, payload[1:]
        return False, None


    def cc2ModifyBillOperatingMode(self, stacker=True, escrow=True):
        # Modify bill operating mode
        for _ in range(pbg.cc2_cmd_retries):
            cc2_cmd = 153

            bitval = 0
            if stacker:
                bitval += BitMask.B0 * 1
            if escrow:
                bitval += BitMask.B1 * 1
            payload = b2s(struct.pack('B', bitval))

            succ, rx_data, key = self.cc2_single_cmd(header=cc2_cmd, payload=payload)
            if not succ:
                print('no response on cmd', cc2_cmd)
                time.sleep(pbg.cc2_cmd_retry_delay)
                continue
            else:
                cc2response = ccTalkMessage(data=b2s(rx_data))
                print("Response: ", cc2response.payload.headerType)
                print_hex(cc2response.raw())

                if cc2response.payload.header == 6:
                    # Busy
                    print('Busy response on cmd', cc2_cmd)
                    time.sleep(pbg.cc2_cmd_retry_delay)
                    continue
                if cc2response.payload.header == 5:
                    # NAK
                    print('NAK response on cmd', cc2_cmd)
                    #raise CustomException('NAK response on cmd')
                    break

                payload = cc2response.getPayload()
                return True, payload[1:]
        return False, None
                

    def cc2ModifyInhibitStatus(self):
        # Modify inhibit status
        for _ in range(pbg.cc2_cmd_retries):
            cc2_cmd = 231

            if self._parentDeviceObj is None:
                raise CustomException('need parent object to get inhibit status')
                
            bitval1, bitval2 = self._parentDeviceObj.getInhibitStatus()
            
            payload = b2s(struct.pack('BB', bitval1, bitval2))

            succ, rx_data, key = self.cc2_single_cmd(header=cc2_cmd, payload=payload)
            if not succ:
                print('no response on cmd', cc2_cmd)
                time.sleep(pbg.cc2_cmd_retry_delay)
                continue
            else:
                cc2response = ccTalkMessage(data=b2s(rx_data))
                print("Response: ", cc2response.payload.headerType)
                print_hex(cc2response.raw())

                if cc2response.payload.header == 6:
                    # Busy
                    print('Busy response on cmd', cc2_cmd)
                    time.sleep(pbg.cc2_cmd_retry_delay)
                    continue
                if cc2response.payload.header == 5:
                    # NAK
                    print('NAK response on cmd', cc2_cmd)
                    #raise CustomException('NAK response on cmd')
                    break

                payload = cc2response.getPayload()
                return True, payload[1:]
        return False, None


    def cc2GetCashboxOperationData(self):
        # Get Cashbox Operation Data
        for _ in range(pbg.cc2_cmd_retries):
            cc2_cmd = 52
            succ, rx_data, key = self.cc2_single_cmd(header=cc2_cmd)
            if not succ:
                print('no response on cmd', cc2_cmd)
                time.sleep(pbg.cc2_cmd_retry_delay)
                continue
            else:
                cc2response = ccTalkMessage(data=b2s(rx_data))
                print("Response: ", cc2response.payload.headerType)
                print_hex(cc2response.raw())

                if cc2response.payload.header == 6:
                    # Busy
                    print('Busy response on cmd', cc2_cmd)
                    time.sleep(pbg.cc2_cmd_retry_delay)
                    continue
                if cc2response.payload.header == 5:
                    # NAK
                    print('NAK response on cmd', cc2_cmd)
                    #raise CustomException('NAK response on cmd')
                    break

                payload = cc2response.getPayload()
                if self._parentDeviceObj is not None:
                    self._parentDeviceObj.initLevels(payload[1:])
                return True, payload[1:]
        return False, None


    def cc2RequestStatus_Cur(self):
        # Request Status (cur)
        for _ in range(pbg.cc2_cmd_retries):
            cc2_cmd = 47
            succ, rx_data, key = self.cc2_single_cmd(header=cc2_cmd)
            if not succ:
                print('no response on cmd', cc2_cmd)
                time.sleep(pbg.cc2_cmd_retry_delay)
                continue
            else:
                cc2response = ccTalkMessage(data=b2s(rx_data))
                print("Response: ", cc2response.payload.headerType)
                print_hex(cc2response.raw())

                if cc2response.payload.header == 6:
                    # Busy
                    print('Busy response on cmd', cc2_cmd)
                    time.sleep(pbg.cc2_cmd_retry_delay)
                    continue
                if cc2response.payload.header == 5:
                    # NAK
                    print('NAK response on cmd', cc2_cmd)
                    #raise CustomException('NAK response on cmd')
                    break

                payload = cc2response.getPayload()
                cc2response.payload.parsePayload(header=cc2_cmd)
                return True, payload[1:], cc2response.payload.eventData_Cur
        return False, None, None


    def cc2RequestStatus(self):
        # Request Status
        for _ in range(pbg.cc2_cmd_retries):
            cc2_cmd = 29
            succ, rx_data, key = self.cc2_single_cmd(header=cc2_cmd)
            if not succ:
                print('no response on cmd', cc2_cmd)
                time.sleep(pbg.cc2_cmd_retry_delay)
                continue
            else:
                cc2response = ccTalkMessage(data=b2s(rx_data))
                if not self.quiet:
                    print("Response: ", cc2response.payload.headerType)
                    print_hex(cc2response.raw())

                if cc2response.payload.header == 6:
                    # Busy
                    print('Busy response on cmd', cc2_cmd)
                    time.sleep(pbg.cc2_cmd_retry_delay)
                    continue
                if cc2response.payload.header == 5:
                    # NAK
                    print('NAK response on cmd', cc2_cmd)
                    #raise CustomException('NAK response on cmd')
                    break

                payload = cc2response.getPayload()
                cc2response.payload.parsePayload(header=cc2_cmd)
                return True, payload[1:], cc2response.payload.eventData
        return False, None, None


    def cc2ReadBufferedBillEvents(self, mode='JCM'):
        # Read buffered bill events
        for _ in range(pbg.cc2_cmd_retries):
            if mode == 'JCM':
                # read where the bill ended out - RC boxes or Cashbox
                cc2_cmd = 59
            else:
                cc2_cmd = 159
            succ, rx_data, key = self.cc2_single_cmd(header=cc2_cmd)
            if not succ:
                print('no response on cmd', cc2_cmd)
                time.sleep(pbg.cc2_cmd_retry_delay)
                continue
            else:
                cc2response = ccTalkMessage(data=b2s(rx_data))
                if not self.quiet:
                    print("Response: ", cc2response.payload.headerType)
                    print_hex(cc2response.raw())

                if cc2response.payload.header == 6:
                    # Busy
                    print('Busy response on cmd', cc2_cmd)
                    time.sleep(pbg.cc2_cmd_retry_delay)
                    continue
                if cc2response.payload.header == 5:
                    # NAK
                    print('NAK response on cmd', cc2_cmd)
                    #raise CustomException('NAK response on cmd')
                    break

                payload = cc2response.getPayload()
                cc2response.payload.parsePayload(header=cc2_cmd)
                return True, payload[1:], cc2response.payload.eventData
        return False, None, None


    def cc2GetDeviceSetup_Cur(self):
        # Get Device Setup (cur)
        for _ in range(pbg.cc2_cmd_retries):
            cc2_cmd = 46
            succ, rx_data, key = self.cc2_single_cmd(header=cc2_cmd)
            if not succ:
                print('no response on cmd', cc2_cmd)
                time.sleep(pbg.cc2_cmd_retry_delay)
                continue
            else:
                cc2response = ccTalkMessage(data=b2s(rx_data))
                print("Response: ", cc2response.payload.headerType)
                print_hex(cc2response.raw())

                if cc2response.payload.header == 6:
                    # Busy
                    print('Busy response on cmd', cc2_cmd)
                    time.sleep(pbg.cc2_cmd_retry_delay)
                    continue
                if cc2response.payload.header == 5:
                    # NAK
                    print('NAK response on cmd', cc2_cmd)
                    #raise CustomException('NAK response on cmd')
                    break

                payload = cc2response.getPayload()
                if self._parentDeviceObj is not None:
                    self._parentDeviceObj.initDenoms(payload[1:])
                return True, payload[1:]
        return False, None


    def cc2RequestAddressMode(self):
        # Request Address Mode
        for _ in range(pbg.cc2_cmd_retries):
            cc2_cmd = 169
            succ, rx_data, key = self.cc2_single_cmd(header=cc2_cmd)
            if not succ:
                print('no response on cmd', cc2_cmd)
                time.sleep(pbg.cc2_cmd_retry_delay)
                continue
            else:
                cc2response = ccTalkMessage(data=b2s(rx_data))
                print("Response: ", cc2response.payload.headerType)
                print_hex(cc2response.raw())

                if cc2response.payload.header == 6:
                    # Busy
                    print('Busy response on cmd', cc2_cmd)
                    time.sleep(pbg.cc2_cmd_retry_delay)
                    continue
                if cc2response.payload.header == 5:
                    # NAK
                    print('NAK response on cmd', cc2_cmd)
                    #raise CustomException('NAK response on cmd')
                    break

                payload = cc2response.getPayload()
                return True, payload[1:]
        return False, None


    def cc2PayoutAmount(self, payout_amt):
        # Payout Amount
        for _ in range(pbg.cc2_cmd_retries):
            cc2_cmd = 22
            payload = b2s(struct.pack('<I', payout_amt))
            
            succ, rx_data, key = self.cc2_single_cmd(header=cc2_cmd, payload=payload)
            if not succ:
                print('no response on cmd', cc2_cmd)
                time.sleep(pbg.cc2_cmd_retry_delay)
                continue
            else:
                cc2response = ccTalkMessage(data=b2s(rx_data))
                print("Response: ", cc2response.payload.headerType)
                print_hex(cc2response.raw())

                if cc2response.payload.header == 6:
                    # Busy
                    print('Busy response on cmd', cc2_cmd)
                    time.sleep(pbg.cc2_cmd_retry_delay)
                    continue
                if cc2response.payload.header == 5:
                    # NAK
                    print('NAK response on cmd', cc2_cmd)
                    #raise CustomException('NAK response on cmd')
                    break

                payload = cc2response.getPayload()
                return True, payload[1:]
        return False, None


    def cc2PayoutByDenomination_Cur(self):
        # Payout By Denomination (cur)
        for _ in range(pbg.cc2_cmd_retries):
            cc2_cmd = 44
            payload = ''
            num_denoms = 0
            for denom in self._parentDeviceObj.denoms:
                if denom['qty'] == 0:
                    continue
                num_denoms += 1
                payload += b2s(struct.pack('<H', denom['qty']))
                payload += b2s(struct.pack('<I', denom['val']))
                payload += denom['cur']
            
            succ, rx_data, key = self.cc2_single_cmd(header=cc2_cmd, payload=b2s(struct.pack('<B', num_denoms))+payload)
            if not succ:
                print('no response on cmd', cc2_cmd)
                time.sleep(pbg.cc2_cmd_retry_delay)
                continue
            else:
                cc2response = ccTalkMessage(data=b2s(rx_data))
                print("Response: ", cc2response.payload.headerType)
                print_hex(cc2response.raw())

                if cc2response.payload.header == 6:
                    # Busy
                    print('Busy response on cmd', cc2_cmd)
                    time.sleep(pbg.cc2_cmd_retry_delay)
                    continue
                if cc2response.payload.header == 5:
                    # NAK
                    print('NAK response on cmd', cc2_cmd)
                    #raise CustomException('NAK response on cmd')
                    break

                payload = cc2response.getPayload()
                return True, payload[1:]
        return False, None


    def cc2GetRouting_Cur(self):
        # Get Routing (cur)
        cc2_cmd = 38
        no_errors = True
        for i in range(len(self._parentDeviceObj.denoms)):
            denom = self._parentDeviceObj.denoms[i]
            payload = ''
            payload += b2s(struct.pack('<I', denom['val']))
            payload += denom['cur']
        
            for _ in range(pbg.cc2_cmd_retries):
                succ, rx_data, key = self.cc2_single_cmd(header=cc2_cmd, payload=payload)
                if not succ:
                    print('no response on cmd', cc2_cmd)
                    time.sleep(pbg.cc2_cmd_retry_delay)
                    continue
                else:
                    cc2response = ccTalkMessage(data=b2s(rx_data))
                    print("Response: ", cc2response.payload.headerType)
                    print_hex(cc2response.raw())

                    if cc2response.payload.header == 6:
                        # Busy
                        print('Busy response on cmd', cc2_cmd)
                        time.sleep(pbg.cc2_cmd_retry_delay)
                        continue
                    if cc2response.payload.header == 5:
                        # NAK
                        print('NAK response on cmd', cc2_cmd)
                        no_errors = False
                        #raise CustomException('NAK response on cmd')
                        break

                    payload = cc2response.getPayload()
                    denom['rut'] = ord(payload[1])
                    self._parentDeviceObj.denoms[i] = denom
                    # break the retry loop
                    break
            else:
                no_errors = False
            # delay more than interchar timeout 50ms
            time.sleep(pbg.hopper_min_delay_time)
        return no_errors


    def cc2SetRouting_Cur(self):
        # Set Routing (cur)
        cc2_cmd = 37
        no_errors = True
        for i in range(len(self._parentDeviceObj.denoms)):
            denom = self._parentDeviceObj.denoms[i]
            #payload = '\x00' 
            # 0=payout, 1=cashbox
            payload = b2s(struct.pack('<B', denom['rut']))
            payload += b2s(struct.pack('<I', denom['val']))
            payload += denom['cur']
        
            for _ in range(pbg.cc2_cmd_retries):
                succ, rx_data, key = self.cc2_single_cmd(header=cc2_cmd, payload=payload)
                if not succ:
                    print('no response on cmd', cc2_cmd)
                    time.sleep(pbg.cc2_cmd_retry_delay)
                    continue
                else:
                    cc2response = ccTalkMessage(data=b2s(rx_data))
                    print("Response: ", cc2response.payload.headerType)
                    print_hex(cc2response.raw())

                    if cc2response.payload.header == 6:
                        # Busy
                        print('Busy response on cmd', cc2_cmd)
                        time.sleep(pbg.cc2_cmd_retry_delay)
                        continue
                    if cc2response.payload.header == 5:
                        # NAK
                        print('NAK response on cmd', cc2_cmd)
                        no_errors = False
                        #raise CustomException('NAK response on cmd')
                        break

                    payload = cc2response.getPayload()
                    # break the retry loop
                    break
            else:
                no_errors = False
            # delay more than interchar timeout 50ms
            time.sleep(pbg.hopper_min_delay_time)
        return no_errors


    def cc2ResetDenominationAmount_Cur(self, value=0):
        # Set Denomination Amount (cur)
        # this allows to set 0 levels or to add to existing levels
        # this method will reset to zero all or given denom value
        
        if value == 0:
            # reset all levels
            print('reset all levels')
        
        cc2_cmd = 43
        no_errors = True
        for i in range(len(self._parentDeviceObj.denoms)):
            denom = self._parentDeviceObj.denoms[i]
            if value != 0:
                if denom['val'] != value:
                    continue
                print('reset level for value', value)

            payload = ''
            payload += b2s(struct.pack('<I', denom['val']))
            payload += b2s(struct.pack('<H', denom['lvl']))
            payload += denom['cur']
        
            for _ in range(pbg.cc2_cmd_retries):
                succ, rx_data, key = self.cc2_single_cmd(header=cc2_cmd, payload=payload)
                if not succ:
                    print('no response on cmd', cc2_cmd)
                    time.sleep(pbg.cc2_cmd_retry_delay)
                    continue
                else:
                    cc2response = ccTalkMessage(data=b2s(rx_data))
                    print("Response: ", cc2response.payload.headerType)
                    print_hex(cc2response.raw())

                    if cc2response.payload.header == 6:
                        # Busy
                        print('Busy response on cmd', cc2_cmd)
                        time.sleep(pbg.cc2_cmd_retry_delay)
                        continue
                    if cc2response.payload.header == 5:
                        # NAK
                        print('NAK response on cmd', cc2_cmd)
                        no_errors = False
                        #raise CustomException('NAK response on cmd')
                        break

                    payload = cc2response.getPayload()
                    # break the retry loop
                    break
            else:
                no_errors = False
            # delay more than interchar timeout 50ms
            time.sleep(pbg.hopper_min_delay_time)
        return no_errors


    def cc2AddDenominationAmount_Cur(self, value=0, level=0):
        # Set Denomination Amount (cur)
        # this allows to set 0 levels or to add to existing levels
        # this method will topup all or given denom value
        
        if value == 0:
            # topup all levels
            print('topup all levels by ', level)
        
        cc2_cmd = 43
        no_errors = True
        for i in range(len(self._parentDeviceObj.denoms)):
            denom = self._parentDeviceObj.denoms[i]
            if value != 0:
                if denom['val'] != value:
                    continue
                print('topup level by %d for value %d' % (level, value))

            denom['lvl'] += level
                
            payload = ''
            payload += b2s(struct.pack('<I', denom['val']))
            payload += b2s(struct.pack('<H', level))
            payload += denom['cur']
        
            for _ in range(pbg.cc2_cmd_retries):
                succ, rx_data, key = self.cc2_single_cmd(header=cc2_cmd, payload=payload)
                if not succ:
                    print('no response on cmd', cc2_cmd)
                    time.sleep(pbg.cc2_cmd_retry_delay)
                    continue
                else:
                    cc2response = ccTalkMessage(data=b2s(rx_data))
                    print("Response: ", cc2response.payload.headerType)
                    print_hex(cc2response.raw())

                    if cc2response.payload.header == 6:
                        # Busy
                        print('Busy response on cmd', cc2_cmd)
                        time.sleep(pbg.cc2_cmd_retry_delay)
                        continue
                    if cc2response.payload.header == 5:
                        # NAK
                        print('NAK response on cmd', cc2_cmd)
                        no_errors = False
                        #raise CustomException('NAK response on cmd')
                        break

                    payload = cc2response.getPayload()
                    
                    self._parentDeviceObj.denoms[i] = denom
                    # break the retry loop
                    break
            else:
                no_errors = False
            # delay more than interchar timeout 50ms
            time.sleep(pbg.hopper_min_delay_time)
        return no_errors


    def cc2GetDenominationAmount_Cur(self, value=0):
        # Get Denomination Amount (cur)
        
        if value == 0:
            # get all levels
            print('get all levels')
            
        cc2_cmd = 42
        no_errors = True
        for i in range(len(self._parentDeviceObj.denoms)):
            denom = self._parentDeviceObj.denoms[i]
        
            if value != 0:
                if denom['val'] != value:
                    continue
                print('get level for value ', value)
                
            payload = ''
            payload += b2s(struct.pack('<I', denom['val']))
            payload += denom['cur']
        
            for _ in range(pbg.cc2_cmd_retries):
                succ, rx_data, key = self.cc2_single_cmd(header=cc2_cmd, payload=payload)
                if not succ:
                    print('no response on cmd', cc2_cmd)
                    time.sleep(pbg.cc2_cmd_retry_delay)
                    continue
                else:
                    cc2response = ccTalkMessage(data=b2s(rx_data))
                    print("Response: ", cc2response.payload.headerType)
                    print_hex(cc2response.raw())

                    if cc2response.payload.header == 6:
                        # Busy
                        print('Busy response on cmd', cc2_cmd)
                        time.sleep(pbg.cc2_cmd_retry_delay)
                        continue
                    if cc2response.payload.header == 5:
                        # NAK
                        print('NAK response on cmd', cc2_cmd)
                        no_errors = False
                        #raise CustomException('NAK response on cmd')
                        break

                    payload = cc2response.getPayload()
                    
                    denom['lvl'] = struct.unpack('<H', s2b(payload[1:3]))[0]
                    self._parentDeviceObj.denoms[i] = denom
                    # break the retry loop
                    break
            else:
                no_errors = False
            # delay more than interchar timeout 50ms
            time.sleep(pbg.hopper_min_delay_time)
        return no_errors
                

    def cc2RequestRCCurrentCount(self, rc_id):
        # Request RC current count
        # how many notes stored in this RC
        for _ in range(pbg.cc2_cmd_retries):
            cc2_cmd = 36
            payload = b2s(struct.pack('<B', rc_id))
            
            succ, rx_data, key = self.cc2_single_cmd(header=cc2_cmd, payload=payload)
            if not succ:
                print('no response on cmd', cc2_cmd)
                time.sleep(pbg.cc2_cmd_retry_delay)
                continue
            else:
                cc2response = ccTalkMessage(data=b2s(rx_data))
                print("Response: ", cc2response.payload.headerType)
                print_hex(cc2response.raw())

                if cc2response.payload.header == 6:
                    # Busy
                    print('Busy response on cmd', cc2_cmd)
                    time.sleep(pbg.cc2_cmd_retry_delay)
                    continue
                if cc2response.payload.header == 5:
                    # NAK
                    print('NAK response on cmd', cc2_cmd)
                    #raise CustomException('NAK response on cmd')
                    break

                payload = cc2response.getPayload()

                if not self._parentDeviceObj.setLevels(payload[1:]):
                    print('unable to set levels for RC', logl='error')

                return True, payload[1:]
        return False, None


    def cc2RequestRCCount(self, rc_id):
        # Request RC count
        # how many notes CAN BE stored MAX in this RC
        for _ in range(pbg.cc2_cmd_retries):
            cc2_cmd = 34
            payload = b2s(struct.pack('<B', rc_id))
            
            succ, rx_data, key = self.cc2_single_cmd(header=cc2_cmd, payload=payload)
            if not succ:
                print('no response on cmd', cc2_cmd)
                time.sleep(pbg.cc2_cmd_retry_delay)
                continue
            else:
                cc2response = ccTalkMessage(data=b2s(rx_data))
                print("Response: ", cc2response.payload.headerType)
                print_hex(cc2response.raw())

                if cc2response.payload.header == 6:
                    # Busy
                    print('Busy response on cmd', cc2_cmd)
                    time.sleep(pbg.cc2_cmd_retry_delay)
                    continue
                if cc2response.payload.header == 5:
                    # NAK
                    print('NAK response on cmd', cc2_cmd)
                    #raise CustomException('NAK response on cmd')
                    break

                payload = cc2response.getPayload()
                return True, payload[1:]
        return False, None


    def cc2ModifyRCCount(self, rc_id, max_lvl):
        # Modify RC count
        # how many notes CAN BE stored in this RC (0 - use max RC capacity)
        for _ in range(pbg.cc2_cmd_retries):
            cc2_cmd = 35
            payload = b2s(struct.pack('<B', 0)) # SEL byte is 0?
            payload += b2s(struct.pack('<H', max_lvl))
            payload += b2s(struct.pack('<B', rc_id))
            
            succ, rx_data, key = self.cc2_single_cmd(header=cc2_cmd, payload=payload)
            if not succ:
                print('no response on cmd', cc2_cmd)
                time.sleep(pbg.cc2_cmd_retry_delay)
                continue
            else:
                cc2response = ccTalkMessage(data=b2s(rx_data))
                print("Response: ", cc2response.payload.headerType)
                print_hex(cc2response.raw())

                if cc2response.payload.header == 6:
                    # Busy
                    print('Busy response on cmd', cc2_cmd)
                    time.sleep(pbg.cc2_cmd_retry_delay)
                    continue
                if cc2response.payload.header == 5:
                    # NAK
                    print('NAK response on cmd', cc2_cmd)
                    #raise CustomException('NAK response on cmd')
                    break

                payload = cc2response.getPayload()
                return True, payload[1:]
        return False, None


    def cc2ModifyVariableMCSet(self, rc_id, bill_id):
        # Modify variable MC set
        # set denoms to be recycled
        for _ in range(pbg.cc2_cmd_retries):
            cc2_cmd = 32

            payload = b2s(struct.pack('<B', 0)) # SEL byte is 0?
            payload += b2s(struct.pack('<H', bill_id[0]))
            payload += b2s(struct.pack('<B', rc_id[0]))
            payload += b2s(struct.pack('<H', bill_id[1]))
            payload += b2s(struct.pack('<B', rc_id[1]))
            
            succ, rx_data, key = self.cc2_single_cmd(header=cc2_cmd, payload=payload)
            if not succ:
                print('no response on cmd', cc2_cmd)
                time.sleep(pbg.cc2_cmd_retry_delay)
                continue
            else:
                cc2response = ccTalkMessage(data=b2s(rx_data))
                print("Response: ", cc2response.payload.headerType)
                print_hex(cc2response.raw())

                if cc2response.payload.header == 6:
                    # Busy
                    print('Busy response on cmd', cc2_cmd)
                    time.sleep(pbg.cc2_cmd_retry_delay)
                    continue
                if cc2response.payload.header == 5:
                    # NAK
                    print('NAK response on cmd', cc2_cmd)
                    #raise CustomException('NAK response on cmd')
                    break

                payload = cc2response.getPayload()
                return True, payload[1:]
        return False, None


    def cc2RequestRCStatus(self, rc_id):
        # Request RC status
        for _ in range(pbg.cc2_cmd_retries):
            cc2_cmd = 29
            payload = b2s(struct.pack('<B', rc_id))
            
            succ, rx_data, key = self.cc2_single_cmd(header=cc2_cmd, payload=payload)
            if not succ:
                print('no response on cmd', cc2_cmd)
                time.sleep(pbg.cc2_cmd_retry_delay)
                continue
            else:
                cc2response = ccTalkMessage(data=b2s(rx_data))
                print("Response: ", cc2response.payload.headerType)
                print_hex(cc2response.raw())

                if cc2response.payload.header == 6:
                    # Busy
                    print('Busy response on cmd', cc2_cmd)
                    time.sleep(pbg.cc2_cmd_retry_delay)
                    continue
                if cc2response.payload.header == 5:
                    # NAK
                    print('NAK response on cmd', cc2_cmd)
                    #raise CustomException('NAK response on cmd')
                    break

                payload = cc2response.getPayload()

                if self._parentDeviceObj is not None:
                    self._parentDeviceObj.processRCStatus(payload[1:])

                return True, payload[1:]
        return False, None


    def cc2DispenseRCBills(self, rc_box_id, bill_qty):
        # Dispense RC bills
        for _ in range(pbg.cc2_cmd_retries):
            cc2_cmd = 28
            payload = b2s(struct.pack('<B', 0)) # SEL = 0
            sess_key = self._parentDeviceObj.getSessKey()
            payload += b2s(sess_key)
            payload += b2s(struct.pack('<B', bill_qty))
            payload += b2s(struct.pack('<B', rc_box_id))
            
            succ, rx_data, key = self.cc2_single_cmd(header=cc2_cmd, payload=payload)
            if not succ:
                print('no response on cmd', cc2_cmd)
                time.sleep(pbg.cc2_cmd_retry_delay)
                continue
            else:
                cc2response = ccTalkMessage(data=b2s(rx_data))
                print("Response: ", cc2response.payload.headerType)
                print_hex(cc2response.raw())

                if cc2response.payload.header == 6:
                    # Busy
                    print('Busy response on cmd', cc2_cmd)
                    time.sleep(pbg.cc2_cmd_retry_delay)
                    continue
                if cc2response.payload.header == 5:
                    # NAK
                    print('NAK response on cmd', cc2_cmd)
                    #raise CustomException('NAK response on cmd')
                    break

                payload = cc2response.getPayload()
                return True, payload[1:]
        return False, None


    def cc2EnableRC(self, enable=True):
        # Enable RC
        for _ in range(pbg.cc2_cmd_retries):
            cc2_cmd = 27
            if enable:
                payload = b2s(b'\xA5')
            else:
                payload = b2s(b'\xFF')
            
            succ, rx_data, key = self.cc2_single_cmd(header=cc2_cmd, payload=payload)
            if not succ:
                print('no response on cmd', cc2_cmd)
                time.sleep(pbg.cc2_cmd_retry_delay)
                continue
            else:
                cc2response = ccTalkMessage(data=b2s(rx_data))
                print("Response: ", cc2response.payload.headerType)
                print_hex(cc2response.raw())

                if cc2response.payload.header == 6:
                    # Busy
                    print('Busy response on cmd', cc2_cmd)
                    time.sleep(pbg.cc2_cmd_retry_delay)
                    continue
                if cc2response.payload.header == 5:
                    # NAK
                    print('NAK response on cmd', cc2_cmd)
                    #raise CustomException('NAK response on cmd')
                    break

                payload = cc2response.getPayload()
                return True, payload[1:]
        return False, None


    def cc2RequestVariableSet(self, rc_id):
        # Request variable set
        # Get status of Recycler Operation Buttons and
        # also the recycle denominations set in RC
        for _ in range(pbg.cc2_cmd_retries):
            cc2_cmd = 24
            payload = b2s(struct.pack('<B', rc_id))
            
            succ, rx_data, key = self.cc2_single_cmd(header=cc2_cmd, payload=payload)
            if not succ:
                print('no response on cmd', cc2_cmd)
                time.sleep(pbg.cc2_cmd_retry_delay)
                continue
            else:
                cc2response = ccTalkMessage(data=b2s(rx_data))
                print("Response: ", cc2response.payload.headerType)
                print_hex(cc2response.raw())

                if cc2response.payload.header == 6:
                    # Busy
                    print('Busy response on cmd', cc2_cmd)
                    time.sleep(pbg.cc2_cmd_retry_delay)
                    continue
                if cc2response.payload.header == 5:
                    # NAK
                    print('NAK response on cmd', cc2_cmd)
                    #raise CustomException('NAK response on cmd')
                    break

                payload = cc2response.getPayload()
                # payload[1] is button info
                self._parentDeviceObj.setRCBoxBillIds(payload[2:])

                return True, payload[1:]
        return False, None


    def cc2RequestCipherKey(self):
        # Request cipher key
        # Pump RNG must be sent first before this cmd!
        for _ in range(pbg.cc2_cmd_retries):
            cc2_cmd = 23
            
            succ, rx_data, key = self.cc2_single_cmd(header=cc2_cmd)
            if not succ:
                print('no response on cmd', cc2_cmd)
                time.sleep(pbg.cc2_cmd_retry_delay)
                continue
            else:
                cc2response = ccTalkMessage(data=b2s(rx_data))
                print("Response: ", cc2response.payload.headerType)
                print_hex(cc2response.raw())

                if cc2response.payload.header == 6:
                    # Busy
                    print('Busy response on cmd', cc2_cmd)
                    time.sleep(pbg.cc2_cmd_retry_delay)
                    continue
                if cc2response.payload.header == 5:
                    # NAK
                    print('NAK response on cmd', cc2_cmd)
                    #raise CustomException('NAK response on cmd')
                    break

                payload = cc2response.getPayload()
                self._parentDeviceObj.saveSessKey(payload[1:])
                return True, payload[1:]
        return False, None


    def cc2PumpRNG(self, rng_val=None):
        # Pump RNG
        for _ in range(pbg.cc2_cmd_retries):
            cc2_cmd = 22
            if rng_val is None:
                rng_val = self._parentDeviceObj.rng_val
            else:
                self._parentDeviceObj.rng_val = rng_val

            print('using random')
            print_hex(rng_val)
            
            payload = b2s(rng_val)
            
            succ, rx_data, key = self.cc2_single_cmd(header=cc2_cmd, payload=payload)
            if not succ:
                print('no response on cmd', cc2_cmd)
                time.sleep(pbg.cc2_cmd_retry_delay)
                continue
            else:
                cc2response = ccTalkMessage(data=b2s(rx_data))
                print("Response: ", cc2response.payload.headerType)
                print_hex(cc2response.raw())

                if cc2response.payload.header == 6:
                    # Busy
                    print('Busy response on cmd', cc2_cmd)
                    time.sleep(pbg.cc2_cmd_retry_delay)
                    continue
                if cc2response.payload.header == 5:
                    # NAK
                    print('NAK response on cmd', cc2_cmd)
                    #raise CustomException('NAK response on cmd')
                    break

                payload = cc2response.getPayload()
                return True, payload[1:]
        return False, None


    def cc2EmergencyStop(self, rc_id):
        # Emergency stop
        # Send Note at the entrance to the cashbox on timeout
        for _ in range(pbg.cc2_cmd_retries):
            cc2_cmd = 30
            payload = b2s(struct.pack('<B', rc_id))
            # 'collect note'
            payload += b2s(struct.pack('<B', 1))
            
            succ, rx_data, key = self.cc2_single_cmd(header=cc2_cmd, payload=payload)
            if not succ:
                print('no response on cmd', cc2_cmd)
                time.sleep(pbg.cc2_cmd_retry_delay)
                continue
            else:
                cc2response = ccTalkMessage(data=b2s(rx_data))
                print("Response: ", cc2response.payload.headerType)
                print_hex(cc2response.raw())

                if cc2response.payload.header == 6:
                    # Busy
                    print('Busy response on cmd', cc2_cmd)
                    time.sleep(pbg.cc2_cmd_retry_delay)
                    continue
                if cc2response.payload.header == 5:
                    # NAK
                    print('NAK response on cmd', cc2_cmd)
                    #raise CustomException('NAK response on cmd')
                    break

                payload = cc2response.getPayload()
                return True, payload[1:]
        return False, None


    def cc2RequestStoreToCashbox(self, rc_box_id):
        # Request store to Cash box
        # Send Note at the entrance to the cashbox on timeout
        for _ in range(pbg.cc2_cmd_retries):
            cc2_cmd = 31
            payload = b2s(struct.pack('<B', 0))
            payload += b2s(struct.pack('<B', rc_box_id))
            
            succ, rx_data, key = self.cc2_single_cmd(header=cc2_cmd, payload=payload)
            if not succ:
                print('no response on cmd', cc2_cmd)
                time.sleep(pbg.cc2_cmd_retry_delay)
                continue
            else:
                cc2response = ccTalkMessage(data=b2s(rx_data))
                print("Response: ", cc2response.payload.headerType)
                print_hex(cc2response.raw())

                if cc2response.payload.header == 6:
                    # Busy
                    print('Busy response on cmd', cc2_cmd)
                    time.sleep(pbg.cc2_cmd_retry_delay)
                    continue
                if cc2response.payload.header == 5:
                    # NAK
                    print('NAK response on cmd', cc2_cmd)
                    #raise CustomException('NAK response on cmd')
                    break

                payload = cc2response.getPayload()
                return True, payload[1:]
        return False, None

