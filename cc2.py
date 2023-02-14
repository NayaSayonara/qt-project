import pbglobals as pbg
from utils import *
from bitmask import BitMask
from pbce import CustomException

# ccTalk header for Default and Custom devices
headerTypesSet = {
        'DEF' : {
            255 : 'Factory set:up and test',
            254 : 'Simple poll',
            253 : 'Address poll',
            252 : 'Address clash',
            251 : 'Address change',
            250 : 'Address random',
            249 : 'Request polling priority',
            248 : 'Request status',
            247 : 'Request variable set',
            246 : 'Request manufacturer id',
            245 : 'Request equipment category id',
            244 : 'Request product code',
            243 : 'Request database version',
            242 : 'Request serial number',
            241 : 'Request software revision',
            240 : 'Test solenoids',
            239 : 'Operate motors',
            238 : 'Test output lines',
            237 : 'Read input lines',
            236 : 'Read opto states',
            235 : 'Read last credit or error code',
            234 : 'Issue guard code',
            233 : 'Latch output lines',
            232 : 'Perform self:check',
            231 : 'Modify inhibit status',
            230 : 'Request inhibit status',
            229 : 'Read buffered credit or error codes',
            228 : 'Modify master inhibit status',
            227 : 'Request master inhibit status',
            226 : 'Request insertion counter',
            225 : 'Request accept counter',
            224 : 'Dispense coins',
            223 : 'Dispense change',
            222 : 'Modify sorter override status',
            221 : 'Request sorter override status',
            220 : 'One:shot credit',
            219 : 'Enter new PIN number',
            218 : 'Enter PIN number',
            217 : 'Request payout high / low status',
            216 : 'Request data storage availability',
            215 : 'Read data block',
            214 : 'Write data block',
            213 : 'Request option flags',
            212 : 'Request coin position',
            211 : 'Power management control',
            210 : 'Modify sorter paths',
            209 : 'Request sorter paths',
            208 : 'Modify payout absolute count',
            207 : 'Request payout absolute count',
            206 : 'Empty payout',
            205 : 'Request audit information block',
            204 : 'Meter control',
            203 : 'Display control',
            202 : 'Teach mode control',
            201 : 'Request teach status',
            200 : 'Upload coin data',
            199 : 'Configuration to EEPROM',
            198 : 'Counters to EEPROM',
            197 : 'Calculate ROM checksum',
            196 : 'Request creation date',
            195 : 'Request last modification date',
            194 : 'Request reject counter',
            193 : 'Request fraud counter',
            192 : 'Request build code',
            191 : 'Keypad control',
            190 : 'Request payout status',
            189 : 'Modify default sorter path',
            188 : 'Request default sorter path',
            187 : 'Modify payout capacity',
            186 : 'Request payout capacity',
            185 : 'Modify coin id',
            184 : 'Request coin id',
            183 : 'Upload window data',
            182 : 'Download calibration info',
            181 : 'Modify security setting',
            180 : 'Request security setting',
            179 : 'Modify bank select',
            178 : 'Request bank select',
            177 : 'Handheld function',
            176 : 'Request alarm counter',
            175 : 'Modify payout float',
            174 : 'Request payout float',
            173 : 'Request thermistor reading',
            172 : 'Emergency stop',
            171 : 'Request hopper coin',
            170 : 'Request base year',
            169 : 'Request address mode',
            168 : 'Request hopper dispense count',
            167 : 'Dispense hopper coins',
            166 : 'Request hopper status',
            165 : 'Modify variable set',
            164 : 'Enable hopper',
            163 : 'Test hopper',
            162 : 'Modify inhibit and override registers',
            161 : 'Pump RNG',
            160 : 'Request cipher key',
            159 : 'Read buffered bill events',
            158 : 'Modify bill id',
            157 : 'Request bill id',
            156 : 'Request country scaling factor',
            155 : 'Request bill position',
            154 : 'Route bill',
            153 : 'Modify bill operating mode',
            152 : 'Request bill operating mode',
            151 : 'Test lamps',
            150 : 'Request individual accept counter',
            149 : 'Request individual error counter',
            148 : 'Read opto voltages',
            147 : 'Perform stacker cycle',
            146 : 'Operate bi:directional motors',
            145 : 'Request currency revision',
            144 : 'Upload bill tables',
            143 : 'Begin bill table upgrade',
            142 : 'Finish bill table upgrade',
            141 : 'Request firmware upgrade capability',
            140 : 'Upload firmware',
            139 : 'Begin firmware upgrade',
            138 : 'Finish firmware upgrade',
            137 : 'Switch encryption code',
            136 : 'Store encryption code',
            135 : 'Set accept limit',
            134 : 'Dispense hopper value',
            133 : 'Request hopper polling value',
            132 : 'Emergency stop value',
            131 : 'Request hopper coin value',
            130 : 'Request indexed hopper dispense count',
            129 : 'Read barcode data',
            128 : 'Request money in',
            127 : 'Request money out',
            126 : 'Clear money counters',
            125 : 'Pay money out',
            124 : 'Verify money out',
            123 : 'Request activity register',
            122 : 'Request error status',
            121 : 'Purge hopper',
            120 : 'Modify hopper balance',
            119 : 'Request hopper balance',
            118 : 'Modify cashbox value',
            117 : 'Request cashbox value',
            116 : 'Modify real time clock',
            115 : 'Request real time clock',
            114 : 'Request USB id',
            113 : 'Switch baud rate',
            112 : 'Read encrypted events',
            111 : 'Request encryption support',
            110 : 'Switch encryption key',
            109 : 'Request encrypted hopper status',
            108 : 'Request encrypted monetary id',
            6 : 'Busy',
            5 : 'NAK',
            4 : 'Request comms revision',
            3 : 'Clear comms status variables',
            2 : 'Request comms status variables',
            1 : 'Reset device',
            0 : 'ACK',
            },
            
        'ITL' : {
            65 : 'Program',  
            64 : 'Halt',  
            60 : 'Coin Stir',  
            59 : 'Get Coin Acceptance',  
            58 : 'Get Coins Exit',  
            57 : 'Set Cashbox Payout Limit Currency',  
            56 : 'Set Cashbox Payout Limit',  
            53 : 'Get Inhibit Peripheral Device Value',  
            52 : 'Get Cashbox Operation Data',  
            51 : 'Smart Empty',  
            50 : 'Set Inhibit Peripheral Device Value',  
            49 : 'Get Peripheral Device Master Inhibit',  
            48 : 'Set Peripheral Device Master Inhibit',  
            47 : 'Request Status (cur)',  
            46 : 'Get Device Setup (cur)',  
            45 : 'Float By Denomination (cur)',  
            44 : 'Payout By Denomination (cur)',  
            43 : 'Set Denomination Amount (cur)',  
            42 : 'Get Denomination Amount (cur)',  
            41 : 'Get Minimum Payout (cur)',  
            40 : 'Float Amount (cur)',  
            39 : 'Payout Amount (cur)',  
            38 : 'Get Routing (cur)',  
            37 : 'Set Routing (cur)',  
            34 : 'Run Unit Calibration',  
            33 : 'Float By Denomination',  
            32 : 'Payout By Denomination',  
            31 : 'Get Payout Options',  
            30 : 'Set Payout Options',  
            29 : 'Request Status',  
            28 : 'Get Device Setup',  
            27 : 'Set Denomination Amount',  
            26 : 'Get Denomination Amount',  
            25 : 'Get Minimum Payout',  
            24 : 'Empty',  
            23 : 'Float Amount',  
            22 : 'Payout Amount',  
            21 : 'Get Routing',  
            20 : 'Set Routing',  
            },
            
        'JCM' : {
            59 : 'Recycle Read buffered Bill events',  
            53 : 'Modify Recycle Operating Mode',  
            52 : 'Request Recycle Operating Mode',  
            39 : 'Request rc-tracking data',  
            38 : 'Modify settings of RC skew reject',  
            37 : 'Request settings of RC skew reject',  
            36 : 'Request RC current count',  
            35 : 'Modify RC count',  
            34 : 'Request RC count',  
            33 : 'Request RC version',  
            32 : 'Modify variable MC set',  
            31 : 'Request store to Cash box',  
            30 : 'Emergency stop',  
            29 : 'Request RC status',  
            28 : 'Dispense RC bills',  
            27 : 'Enable RC',  
            26 : 'Request total count',  
            25 : 'Modify variable key set',  
            24 : 'Request variable set',  
            23 : 'Request cipher key',  
            22 : 'Pump RNG',  
            21 : 'Clear total count',  
            20 : 'Modify RC current count',  
            },
        }

# SH3 Event types definition
eventTypes = {
        0 : ('Idle', 0, 0),
        1 : ('Dispensing', 4, 8),  
        2 : ('Dispensed', 4, 8),  
        3 : ('Coins Low', 0, 0), 
        4 : ('Empty', 0, 0), 
        5 : ('Jammed', 4, 8), 
        6 : ('Halted', 4, 8), 
        7 : ('Floating', 4, 8), 
        8 : ('Floated', 4, 8), 
        9 : ('Timeout', 4, 8), 
        10 : ('Incomplete Payout', 8, 12), 
        11 : ('Incomplete Float', 8, 12), 
        12 : ('Cashbox Paid', 4, 8), 
        13 : ('Coin Credit', 4, 7), 
        14 : ('Emptying', 0, 0), 
        15 : ('Emptied', 0, 0), 
        16 : ('Fraud Attempt', 4, 8), 
        17 : ('Disabled', 0, 0), 
        19 : ('Slave Reset', 0, 0), 
        33 : ('Lid Open', 0, 0), 
        34 : ('Lid Closed', 0, 0), 
        35 : ('Refill Coin Credit', 0, 0),  
        36 : ('Calibration Fault', 1, 1), 
        37 : ('Attached Mech Jam', 0, 0), 
        38 : ('Attached Mech Open', 0, 0), 
        39 : ('Smart Emptying', 4, 8), 
        40 : ('Smart Emptied', 4, 8), 
        54 : ('Multiple Value Added', 4, 8),  
        55 : ('Peripheral Error', 2, 2),  
        56 : ('Peripheral Device Disabled', 1, 1),  
        58 : ('Value Pay-in', 0, 0),  
        59 : ('Device Full', 0, 0),  
        61 : ('Coin Cashbox', 0, 0), 
        62 : ('Coin Payout', 0, 0), 
        63 : ('Coin Rejected', 0, 0),  
        }

# SH3 payout option byte 1 definition
payoutOptionByte1 = {
        BitMask.B0 : ('Pay mode is high value split', 'Pay mode is free pay'),
        BitMask.B1 : ('Level check disabled', 'Level check enabled'),
        BitMask.B2 : ('Motor speed low', 'Motor speed high'),
        BitMask.B3 : ('Bit 3 not used (0)', 'Bit 3 not used (1)'),
        BitMask.B4 : ('Payout algorithm is normal', 'Payout algorithm is high speed split'),
        BitMask.B5 : ('Unknown coin route is cashbox', 'Unknown coin route is payout'),
        BitMask.B6 : ('Unknown coin stop is disabled', 'Unknown coin stop is enabled'),
        BitMask.B7 : ('Use cashbox coins in payout disabled', 'Use cashbox coins in payout enabled'),
        }

# SH3 payout option byte 2 definition
payoutOptionByte2 = {
        BitMask.B0 : ('Coin added events disabled', 'Coin added events enabled'),
        BitMask.B1 : ('Level 0 to cashbox disabled', 'Level 0 to cashbox enabled'),
        BitMask.B2 : ('Coin Rejected Events (0)', 'Coin Rejected Events (1)'),
        BitMask.B3 : ('Smart Empty Route (0)', 'Smart Empty Route (1)'),
        BitMask.B4 : ('Coin Reject Full Events (0)', 'Coin Reject Full Events (1)'),
        BitMask.B5 : ('Bit 5 not used (0)', 'Bit 5 not used (1)'),
        BitMask.B6 : ('Bit 6 not used (0)', 'Bit 6 not used (1)'),
        BitMask.B7 : ('Bit 7 not used (0)', 'Bit 7 not used (1)'),
        }


bnvEventTypes = {
        0 : 'Master inhibit active',
        1 : 'Bill returned from escrow',
        2 : 'Invalid bill ( due to validation fail )',
        3 : 'Invalid bill ( due to transport problem )',
        4 : 'Inhibited bill ( on serial )',
        5 : 'Inhibited bill ( on DIP switches )',
        6 : 'Bill jammed in transport ( unsafe mode )',
        7 : 'Bill jammed in stacker',
        8 : 'Bill pulled backwards',
        9 : 'Bill tamper',
        10 : 'Stacker OK',
        11 : 'Stacker removed',
        12 : 'Stacker inserted',
        13 : 'Stacker faulty',
        14 : 'Stacker full',
        15 : 'Stacker jammed',
        16 : 'Bill jammed in transport ( safe mode )',
        17 : 'Opto fraud detected',
        18 : 'String fraud detected',
        19 : 'Anti-string mechanism faulty',
        20 : 'Barcode detected',
        21 : 'Unknown bill type stacked',
        # JCM BNV specific
        51 : 'Recycler error',
        52 : 'Recycle unit removed',
        53 : 'Recycle unit insert',
        54 : 'Recycle unit OK',
        }

class ccTalkPayload():

    def __init__(self, header='0', data='', header_set=['DEF']):
        try:
            self.header = int(header)
        except TypeError:
            self.header = 0
        self.data = data
        self.decodedHeader = ''
        self.header_set = header_set
        if self.header != '':
            for header_rec in header_set:
                if self.header in headerTypesSet[header_rec]:
                    self.headerType = headerTypesSet[header_rec][self.header]
                    break
            else:
                self.headerType = 'Unknown'
        else:
            self.headerType = ''

        #print('Using header set', self.header_set)
        #print('Found header type', self.headerType)

        self.eventData = []
        self.eventData_Cur = []

    def parsePayload(self, header=0):
        #Analyzing a response
        if self.header == 0:
            if header == 230 or header == 231:
                #Process inhibit status
                return self._extractChannelData()
            elif header == 229:
                #Process coin event code status
                return self._extractCoinBuffer()
            elif header in [131, 145, 170, 171, 184, 192, 241, 242, 244, 245,
                    246]:
                #Process functions that return ASCII
                self.decodedHeader = str(self.data)
                return self.decodedHeader
            elif header == 227:
                return self._extractEnableState()
            elif header == 47 and 'ITL' in self.header_set:
                # request status (cur)
                self.eventData_Cur = []
                #print(len(self.data))
                #print_hex(self.data)
                try:
                    evt_offset = 0
                    while True:
                        evt_code = ord(self.data[evt_offset])
                        evt_type, _, evt_data_len = eventTypes[evt_code]
                        evt_data = self.data[evt_offset+1:evt_offset+1+evt_data_len]
                        evt_offset += 1 + evt_data_len # event code + its data
                        self.eventData_Cur.append((evt_code, evt_data, evt_type))
                        if evt_offset >= len(self.data):
                            break
                except KeyError:
                    self.eventData_Cur.append((evt_code, [], 'Unknown Event'))
                    raise CustomException('undefined event; parser stopped')
                return self.data
            elif header == 29 and 'ITL' in self.header_set:
                # request status 
                self.eventData = []
                #print(len(self.data))
                #print_hex(self.data)
                try:
                    evt_offset = 0
                    while True:
                        evt_code = ord(self.data[evt_offset])
                        evt_type, evt_data_len, _ = eventTypes[evt_code]
                        evt_data = self.data[evt_offset+1:evt_offset+1+evt_data_len]
                        evt_offset += 1 + evt_data_len # event code + its data
                        self.eventData.append((evt_code, evt_data, evt_type))
                        if evt_offset >= len(self.data):
                            break
                except KeyError:
                    self.eventData.append((evt_code, [], 'Unknown Event'))
                    raise CustomException('undefined event; parser stopped')
                return self.data
            elif header == 31 and 'ITL' in self.header_set:
                # Get Payout Options
                print('Opt Byte1 %02x' % ord(self.data[0]))
                for bit_mask, bit_vals in payoutOptionByte1.items():
                    #bit_vals = payoutOptionByte1[bit_mask]
                    if ord(self.data[0]) & bit_mask:
                        print('Opt Byte1 %02x' % bit_mask, bit_vals[1])
                    else:
                        print('Opt Byte1 %02x' % bit_mask, bit_vals[0])
                print('Opt Byte2 %02x' % ord(self.data[1]))
                for bit_mask, bit_vals in payoutOptionByte2.items():
                    #bit_vals = payoutOptionByte2[bit_mask]
                    if ord(self.data[1]) & bit_mask:
                        print('Opt Byte2 %02x' % bit_mask, bit_vals[1])
                    else:
                        print('Opt Byte2 %02x' % bit_mask, bit_vals[0])
                return self.data
            elif header == 30 and 'ITL' in self.header_set:
                # Set Payout Options
                pass
            elif header == 159 or (header == 59 and 'JCM' in self.header_set):
                # Read buffered bill events
                # note this will flood non-legitimate 'Master inhibit active'
                # when evt_counter for that event is 0
                
                self.eventData = []
                #print(len(self.data))
                #print_hex(self.data)
                try:
                    evt_offset = 0
                    evt_counter = ord(self.data[evt_offset])
                    evt_offset += 1
                        
                    for _ in range(5):
                        evt_codeA = ord(self.data[evt_offset])
                        evt_codeB = ord(self.data[evt_offset+1])
                        if evt_codeA == 0:
                            # status or error
                            evt_type = bnvEventTypes[evt_codeB]
                        else:
                            # credit or pending credit
                            if evt_codeB == 0:
                                evt_type = 'Credit'
                            elif evt_codeB == 1:
                                evt_type = 'Pending Credit'
                            elif evt_codeB == 30:
                                evt_type = 'Credit (Bill in CashBox)'
                            elif evt_codeB == 31:
                                evt_type = 'Credit (Bill in RC Box 1)'
                            elif evt_codeB == 32:
                                evt_type = 'Credit (Bill in RC Box 2)'
                            else:
                                evt_type = 'Unspecified Event'

                        self.eventData.append((evt_counter, evt_codeA, evt_codeB, evt_type))

                        evt_offset += 2
                        if evt_offset >= len(self.data):
                            break

                except KeyError:
                    self.eventData.append((evt_counter, evt_codeA, evt_codeB, 'Unknown Event'))
                    raise CustomException('undefined event; parser stopped')
                return self.data
            else:
                #self.decodedHeader = self.data.encode('hex')
                #return self.decodedHeader
                return self.data
        #Anlyzing a request
        else:
            if self.header == 231:
                return self._extractChannelData()
            elif self.header == 228:
                return self._extractEnableState()
            elif self.header in [184, 209]:
                return self._extractChannelInfo()
            else:
                self.decodedHeader = self.data.encode('hex')
                return self.decodedHeader

    def __repr__(self):
        """
        Returns a byte string representing the ccTalk payload
        """
        return chr(self.header) + self.data

    def _extractEnableState(self):
        if self.data == '\x01':
            self.decodedHeader = "State enabled"
        else:
            self.decodedHeader = "State disabled"
        return self.decodedHeader

    def _extractChannelInfo(self):
        self.decodedHeader = "Channel "+str(ord(self.data))
        return self.decodedHeader

    def _extractCoinBuffer(self):
        """
        Extracts event buffer response from request 229
        """
        data = self.data[1:]
        eventCpt = ord(self.data[0])
        self.decodedHeader = "Event Counter : "+str(eventCpt)+"\n"
        for resultA, resultB in zip(data, data[1:])[::2]:
            self.decodedHeader = self.decodedHeader + "Result A "+\
                    str(ord(resultA))+" - Result B "+str(ord(resultB))+"\n"
        self.decodedHeader = self.decodedHeader.strip()
        return self.decodedHeader

    def _extractChannelData(self):
        """
        Extract channel data
        Used with Headers 230 and 231 (Modify/Request Inhibit status)
        Gets the two bytes input and sends back an array containing the
        channel status
        1 - enabled
        0 - disabled
        """
        channels = []
        for byte in self.data:
            for bit in self._extractBits(ord(byte)):
                channels.append(bit)
            ch = 1
            enabledChannels = []
            disabledChannels = []
            for channel in channels:
                if channel == 1:
                    enabledChannels.append(ch)
                else:
                    disabledChannels.append(ch)
                ch = ch + 1
        self.decodedHeader = "Enabled channels : " + str(enabledChannels) + \
                "\nDisabled channels : " + str(disabledChannels)
        return self.decodedHeader

    def _extractBits(self, byte):
        for i in range(8):
            yield (byte >> i) & 1


class ccTalkMessage():
    def __init__(self, data='', source=1, destination=2, header=0, payload='', force_crc_err=False):
        # ccTalkPayload will need a ccTalk header set to use
        # a proper way would be to pass that param to the constructor
        # which is used every time there is ccTalk comms - awkward!
        # an ugly shortcut is to check the device we work with via
        # its global address equal to setting pbg.hopper_cc2_address
        # or pbg.bnv_cc2_address
            
        if data == '':
            #Creates a blank message
            self.destination = destination
            self.length = len(payload)
            self.source = source
            data = payload
            self.sigmode = 0
        elif self._validateChecksum(data) and not force_crc_err:
            #Generates a message using raw data (Checksum)
            self.destination = ord(data[0])
            self.length = ord(data[1])
            self.source = ord(data[2])
            header = ord(data[3])
            data = data[4:-1]
            self.sigmode = 0
        elif self._validateCRC(data) and not force_crc_err:
            #Generates a message using raw data (CRC)
            self.destination = ord(data[0])
            self.length = ord(data[1])
            self.source = 1     #Source is always assumed to be 1 in CRC mode
            header = ord(data[3])
            data = data[4:-1]
            self.sigmode = 1
        else:
            # checksum failure
            #raise CustomException('checksum failure')
            # simulate 'busy' response - this will force a retry
            self.destination = 1
            self.length = 0
            self.source = 1
            # Busy! Sort of..
            header = 6
            data = ''
            self.sigmode = 0

        if self.destination == pbg.hopper_cc2_address or self.source == pbg.hopper_cc2_address:
            self._header_set = ['DEF', 'ITL']
        elif self.destination == pbg.bnv_cc2_address or self.source == pbg.bnv_cc2_address:
            self._header_set = ['DEF', 'JCM']
        else:
            self._header_set = ['DEF']
            
        #print('src and dest', self.source, self.destination, self._header_set)
        self.payload = ccTalkPayload(header, data, header_set=self._header_set)

    def raw(self):
        """
        Returns a byte string representing the ccTalk message
        """
        if self.sigmode == 0:
            return chr(self.destination)+chr(self.length)+chr(self.source)+\
                    repr(self.payload)+chr(self._calculateChecksum())
        else:
            crc = self._calculateCRC()
            return chr(self.destination)+chr(self.length)+chr(crc & 0xff)+\
                    repr(self.payload)+chr((crc & 0xff00) >> 8)


    def __len__(self):
        return len(chr(self.destination)+chr(self.length)+chr(self.source)+\
                repr(self.payload)+1)

    def __repr__(self):
        """
        Returns a byte string representing the ccTalk message
        """
        if self.sigmode == 0:
            return repr(chr(self.destination)+chr(self.length)+\
                    chr(self.source)+repr(self.payload)+\
                    chr(self._calculateChecksum()))
        else:
            crc = self._calculateCRC()
            return repr(chr(self.destination)+chr(self.length)+\
                    chr(crc & 0xff)+repr(self.payload)+\
                    chr((crc & 0xff00) >> 8))

    def __str__(self):
        """
        Returns a user-friendly representation of the message
        """
        if self.sigmode == 0:
            signature = 'checksum'
        else:
            signature = 'CRC'
        if self.payload.data != "":
            return "<cctalk src="+str(self.source)+" dst="+\
                    str(self.destination)+" length="+str(self.length)+\
                    " header="+str(self.payload.header)+\
                    " data="+self.payload.data.encode('hex')+\
                    " signature="+signature+">"
        else:
            return "<cctalk src="+str(self.source)+" dst="+\
                    str(self.destination)+" length="+str(self.length)+\
                    " header="+str(self.payload.header)+\
                    " signature="+signature+">"

    def setPayload(self, header, data=''):
        """
        Creates a new payload for the message
        """
        self.payload = ccTalkPayload(header, data, header_set=['DEF'])
        self.length = len(data)

    def getPayload(self):
        return repr(self.payload)

    def getPayloadType(self):
        return self.payload.headerType

    def _calculateChecksum(self):
        """
        Calculates the checksum for the message
        """
        data = chr(self.destination)+chr(self.length)+chr(self.source)+\
                repr(self.payload)
        total = 0
        for byte in data:
            total = total + ord(byte)
        return (256-(total%256))%256

    def _validateChecksum(self, data):
        """
        Validates the checksum of a full message
        """
        if len(data) < 5:
            print("Message too short!", logl='warning')
            print(len(data))
            print_hex(data)
            return False
            
        total = 0
        for byte in data[:-1]:
            total = total + ord(byte)
        final_cs = (256-(total%256))%256
        if final_cs != ord(data[-1]):
            print("Checksum calc vs received ", final_cs, ord(data[-1]), logl='warning')
            print(len(data))
            print_hex(data)
        return (final_cs==ord(data[-1]))

    def _calculateCRC(self, data=None):
        """
        Calculates the CCITT checksum (CRC16) that can be used as a ccTalk
        checksuming algorithm
        """
        if data is None:
            data = chr(self.destination)+chr(self.length)+repr(self.payload)
        crc=0
        poly = 0x1021

        for c in data:
            crc ^= (ord(c) << 8) & 0xffff
            for x in range(8):
                if crc & 0x8000:
                    crc = ((crc << 1) ^ poly) & 0xffff
                else:
                    crc <<= 1
                    crc &= 0xffff
        return crc

    def _validateCRC(self, data):
        """
        Validates the CRC of a full message
        """
        if len(data) < 5:
            print("Message too short!", logl='warning')
            print(len(data))
            print_hex(data)
            return False
            
        crc = ord(data[2]) + (ord(data[-1]) << 8)
        data = data[0:2]+data[3:-1]
        return crc == self._calculateCRC(data)
