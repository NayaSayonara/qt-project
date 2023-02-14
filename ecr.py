import queue
import sys
import threading

import time
import socket
import requests
import inspect


gpSTX = b'\x02'
gpETX = b'\x03'
gpFS = b'\x1C'

gp_link_up = False


gpLINKUP_TO = 120.0
gpRSP_TO = 65.0


class GPTxn:
    def __init__(self, amt=None, inv=None, q_in_=None, q_out_=None):
        # debug
        global inst
        self._inst = inst
        print("GPTxn instance created %d" % self._inst)
        inst += 1

        if inv is None:
            self._gpInvV = 1
        else:
            self._gpInvV = inv

        if amt is None:
            self._gpAmtV = "0"
        else:
            self._gpAmtV = amt

        if q_in_ is not None:
            self._gpQin = q_in_

        if q_out_ is not None:
            self._gpQout = q_out_

        self._gpTID = "        "
        self._gpTimestamp = get_timestamp()
        self._gpMsgType = "T00"
        self._gpMsgTypeRev = "T10"
        self._gpInvF = "S"
        self._gpAmtF = "B"
        self._gpApprovalCodeF = "F"
        # self._gpApprovalCodeV = ""

        self._gpDataLen = b"0"
        self._gpDataCrc = b"0"

        self._gpHdr = b"0"
        self._gpData = b"0"
        self._gpFullReq = b"0"

        self._gpFullRsp = b"0"
        self._gpRspFields = []

    def __del__(self):
        print("GPTxn instance deleted %d" % self._inst)

    def get_gp_timestamp(self):
        return b2s(self._gpTimestamp)

    def set_tid(self, gp_rsp):
        if gp_rsp[0] == b2s(gpSTX):
            self._gpTID = gp_rsp[5:13]
        else:
            self._gpTID = gp_rsp[4:12]
        print("_gpTID set to ", self._gpTID)

    def get_tid(self):
        return self._gpTID

    def set_amt(self, amt):
        self._gpAmtV = undot_amt(amt)
        print("_gpAmtV set to ", self._gpAmtV)

    def get_inv(self):
        return self._gpInvV

    def build_req_sale(self):
        # without data len and crc
        self._gpHdr = b'B001' + s2b(self._gpTID) + self._gpTimestamp + b'0000'
        # amt + txn type + inv
        self._gpData = gpFS + s2b(self._gpAmtF + self._gpAmtV)
        self._gpData += gpFS + s2b(self._gpMsgType)
        self._gpData += gpFS + s2b(self._gpInvF + f"{self._gpInvV:010d}")

        self._gpDataLen = s2b(f"{len(self._gpData):04X}")
        self._gpDataCrc = s2b(f"{CRC_16_CCITT(self._gpData):04X}")

        self._gpHdr += self._gpDataLen + self._gpDataCrc

        self._gpFullReq = gpSTX + self._gpHdr + self._gpData + gpETX
        print("Full req sale is ", self._gpFullReq)

    def build_req_reversal(self):
        # without data len and crc
        self._gpHdr = b'B001' + s2b(self._gpTID) + self._gpTimestamp + b'0000'
        # amt + txn type + auth code
        self._gpData = gpFS + s2b(self._gpAmtF + self._gpAmtV)
        self._gpData += gpFS + s2b(self._gpMsgTypeRev)

        succ, approval_code = self.get_gp_rsp_approval_code()
        if succ:
            self._gpData += gpFS + s2b(self._gpApprovalCodeF + approval_code)
            # self._gpData += gpFS + s2b(self._gpApprovalCodeF + self._gpApprovalCodeV)
        else:
            print("BUG: unable to supply approval code for reversal req to POS ", logl='error')
            self._gpData += gpFS + s2b(self._gpApprovalCodeF + "")

        # self._gpData += gpFS + s2b(self._gpInvF + f"{self._gpInvV:010d}")

        self._gpDataLen = s2b(f"{len(self._gpData):04X}")
        self._gpDataCrc = s2b(f"{CRC_16_CCITT(self._gpData):04X}")

        self._gpHdr += self._gpDataLen + self._gpDataCrc

        self._gpFullReq = gpSTX + self._gpHdr + self._gpData + gpETX
        print("Full req reversal is ", self._gpFullReq)

    def build_req_conf(self):
        # without data len and crc
        self._gpHdr = b'B001' + s2b(self._gpTID) + self._gpTimestamp + b'0000'
        # no data section
        self._gpData = b""

        self._gpDataLen = s2b(f"{len(self._gpData):04X}")
        # spec is ambiguous whether this should be 0000 or A5A5
        # self._gpDataCrc = s2b(f"{CRC_16_CCITT(self._gpData):04X}")
        # self._gpDataCrc = s2b("A5A5")
        self._gpDataCrc = s2b("0000")

        self._gpHdr += self._gpDataLen + self._gpDataCrc

        self._gpFullReq = gpSTX + self._gpHdr + self._gpData + gpETX
        print("Full req conf is ", self._gpFullReq)

    def end_gp_sess(self):
        self._gpQin.put((False, b''))

    def send_gp_req(self, final=False):
        if self._gpQin is None:
            print("Faking ", self._gpFullReq)
            pass
        else:
            poll_int = 0.5
            poll_wait = 0.0
            while poll_wait < gpLINKUP_TO:
                if not gp_link_up:
                    print("gp link not up, wait", gp_link_up)
                    time.sleep(poll_int)
                    poll_wait += poll_int
                else:
                    print("gp link up, proceed to send req", gp_link_up)
                    break

            if final:
                self._gpQin.put((False, self._gpFullReq))
            else:
                print("Sending ", self._gpFullReq)
                self._gpQin.put((True, self._gpFullReq))

    def get_gp_rsp(self, conf=False):
        if self._gpQout is None:
            print("Faking rsp")

            rsp_dummy1 = gpSTX + b'B001S1APDA05140526124328000000499D0E' + gpFS + b'T00' + \
                         gpFS + b'R000' + gpFS + b'P472943*******143' + gpFS + b'F123456 B' + \
                         gpFS + b'aA0000000041010' + gpFS + b'JVISA' + gpFS + b'n140526124333' + gpETX

            rsp_dummy2 = gpSTX + b'B001S1APDA0514052612432800000000A5A5' + gpETX

            if conf:
                self._gpFullRsp = rsp_dummy2
            else:
                self._gpFullRsp = rsp_dummy1
            return True
        else:
            try:
                self._gpFullRsp = self._gpQout.get(timeout=gpRSP_TO)

                print("Got back ", self._gpFullRsp)

                self._gpRspFields = b2s(self._gpFullRsp[1:-1]).split(b2s(gpFS))
                print("Parsed: ", self._gpRspFields)

                self.set_tid(b2s(self._gpFullRsp[1:-1]))
                return True

            except queue.Empty:
                print("POS response timeout.", logl='warning')
                self._gpRspFields = []
                self._gpQin.put((False, b''))
                return False

    def if_gp_rsp_is_conf(self):
        return len(self._gpRspFields) == 1

    def if_gp_rsp_is_sale(self):
        for fld in self._gpRspFields:
            if fld[0] == "T":
                return True
        return False

    def if_gp_sale_approved(self):
        for fld in self._gpRspFields:
            if fld[0] == "R":
                rsp_code = int(fld[1:4])
                print("GP rsp code is ", rsp_code)
                if 0 <= rsp_code <= 10:
                    return True
        return False

    def get_gp_rsp_approval_code(self):
        for fld in self._gpRspFields:
            if fld[0] == "F":
                return True, fld[1:]
        return False, None

    def get_gp_rsp_masked_pan(self):
        for fld in self._gpRspFields:
            if fld[0] == "P":
                return True, fld[1:]
        return False, None

    def get_gp_rsp_receipt(self):
        for fld in self._gpRspFields:
            if fld[0] == "t":
                return True, fld[1:]
        return False, None


def CRC_16_CCITT(msg):
    crc = binascii.crc_hqx(msg, 0)
    return crc


'''
Sale:
ECR : Transaction request
<STX>B001<SPC><SPC><SPC><SPC><SPC><SPC><SPC><SPC>140526124328000000167673
<FS>B1500<FS>T00<FS>S0123456789<ETX>
POST: Confirmation message(s)
<STX>B001 S1APDA05 140526124328 0000 0000 A5A5<ETX>
POST: Transaction response
<STX>B001S1APDA05140526124328000000499D0E<FS>T00<FS>R000<FS>P472943*******143
<FS>F123456<SPC>B<FS>aA0000000041010<FS>JVISA<FS>n140526124333<ETX>
ECR : Confirmation message
<STX>B001 S1APDA05 140526124328 0000 0000 A5A5<ETX>
'''


def gpe_read_socket(connection, tout, q_out_):
    # recv can throw socket.timeout
    connection.settimeout(tout)
    try:
        data = connection.recv(1024)
        print("received %s" % data)
        if data:
            q_out_.put(data)
        else:
            print("no data!", logl='warning')
    except socket.timeout:
        print("no resp from POS", logl='warning')


def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
        print("Critical: unable to get own IP, defaulting to ", IP, logl='error')
    finally:
        s.close()
    return IP


def gpe_heartbeat_thread(q_in_, q_out_, ev_exit):
    print("gpe_heartbeat_thread started")
    # raise CustomException('gpe_heartbeat_thread test exc')
    global gp_link_up

    thread_enabled = True

    while thread_enabled:
        session_active = False

        # Create a TCP/IP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # print ("socket is ", sock.getsockname())
        # print ("local ip is ", socket.gethostbyname(socket.getsockname()))
        def_ip = get_ip()
        print("local ip is ", def_ip)
        # print ("2local ip is ", socket.gethostbyname(socket.getfqdn()))
        # Bind the socket to the port
        server_address = (def_ip, 2050)
        print("starting up on %s port %s" % server_address)

        for _ in range(10):
            try:
                sock.bind(server_address)
                break
            except OSError:
                # this or call
                # sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                # to change behaviour (ignore TIME_WAIT)
                print("bind failed, retrying in 15s", logl='error')
                time.sleep(15.0)

        # Listen for incoming connections
        sock.listen(1)

        # Wait for a connection
        # accept can throw socket.timeout
        sock.settimeout(gpLINKUP_TO)
        print("waiting for a connection")
        try:
            connection, client_address = sock.accept()
        except socket.timeout:
            print("no incoming connection requests", logl='error')
            # connection.close()
            if ev_exit.is_set():
                print("gpe_heartbeat_thread shutdown event")
                thread_enabled = False
                break
            continue
            # exit()

        try:
            print("connection from")
            print(client_address)

            gp_link_up = True

            while thread_enabled:
                if ev_exit.is_set():
                    print("gpe_heartbeat_thread shutdown event")
                    thread_enabled = False
                    break

                if not session_active:
                    try:
                        # print ("sending heartbeat to the POS", gp_link_up)
                        connection.sendall(b'\xFF\xFF')

                        (sess_status, msg_req) = q_in_.get(timeout=5.0)

                        print("got ecr req ", msg_req)
                        if len(msg_req) > 0:
                            connection.sendall(msg_req)

                        if session_active != sess_status:
                            print("got new sess status ", sess_status)
                            session_active = sess_status

                        gpe_read_socket(connection, 1.0, q_out_)

                    except queue.Empty:
                        # print ("no incoming ecr msg")
                        pass
                    except ConnectionError:
                        print("sess: socket reset or connection error, reconnecting...", logl='warning')
                        thread_enabled = True
                        break

                else:  # if not session_active:
                    try:
                        (sess_status, msg_req) = q_in_.get(block=False)

                        print("sess: got ecr req ", msg_req)
                        if len(msg_req) > 0:
                            connection.sendall(msg_req)

                        if session_active != sess_status:
                            print("sess: got new sess status ", sess_status)
                            session_active = sess_status

                        gpe_read_socket(connection, 1.0, q_out_)

                    except queue.Empty:
                        print("sess: no incoming ecr msg")
                        gpe_read_socket(connection, 1.0, q_out_)
                    except ConnectionError:
                        print("sess: socket reset or connection error, reconnecting...", logl='warning')
                        thread_enabled = True
                        break

        finally:
            # Clean up the connection
            print("connection to POS closed")
            connection.close()
            sock.close()
            gp_link_up = False
    print("gpe_heartbeat_thread finished")

