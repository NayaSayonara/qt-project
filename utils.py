import string
import secrets
from logprint import print
from datetime import datetime


def s2b(in_string):
    return bytes(in_string, encoding='latin1')


def b2s(in_bytes):
    return in_bytes.decode("latin1")


def print_hex(pbtData, szBytes=None):
    if szBytes is None:
        szBytes = len(pbtData)
    if szBytes > 0:
        if type(pbtData) is str:
            print("%s" % str(" ".join([f"{ord(pbtData[szPos]):02X}" for szPos in range(szBytes)])))
        else:
            print("%s" % str(" ".join([f"{pbtData[szPos]:02X}" for szPos in range(szBytes)])))
    
 
def print_dec(pbtData, szBytes=None):
    if szBytes is None:
        szBytes = len(pbtData)
    if szBytes > 0:
        if type(pbtData) is str:
            print("%s" % str(" ".join([f"{ord(pbtData[szPos]):03d}" for szPos in range(szBytes)])))
        else:
            print("%s" % str(" ".join([f"{pbtData[szPos]:03d}" for szPos in range(szBytes)])))


def undot_amt(amt):
    if '.' in amt:
        amt_l = amt.split('.')
        if (int(amt_l[0])) == 0:
            return str(int(amt_l[1]))
        else:
            return str(100 * int(amt_l[0]) + int(amt_l[1]))
    else:
        return amt


def dot_amt(amt):
    if '.' in amt:
        return amt
    else:
        return "%01d.%02d" % (int(amt) / 100, int(amt) % 100)
 

def get_timestamp():
    date_string = f'{datetime.now():%y%m%d%H%M%S}'
    return bytes(date_string, encoding='latin1')
    
    
def get_pi_serial():
    success = False
    pi_serial = ''
    with open('/proc/cpuinfo', 'r') as f:
        for line in f:
            tokens = [x.strip() for x in line.split(':')]
            if tokens[0] == 'Serial':
                pi_serial = tokens[1]
                success = True
                print("This RPi Serial is ", pi_serial)
    return success, pi_serial


def CRC_16_CCITT(msg):
    crc = binascii.crc_hqx(msg, 0)
    return crc


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

# bit shift left of n by d bits
def lcs(n, d, bits=8):
 
    d = d % bits
    mask = (2 ** bits) - 1
    return ((n << d)|(n >> (bits - d))) & mask
 
# bit shift right of n by d bits
def rcs(n, d, bits=8):
 
    d = d % bits
    mask = (2 ** bits) - 1
    return ((n >> d)|(n << (bits - d))) & mask


def random_bytes(len):
    return secrets.token_bytes(len)
    
# string of decimal digits
def random_string_of_digits(len):
    choice_set = string.digits
    return ''.join(secrets.choice(choice_set) for i in range(len))
