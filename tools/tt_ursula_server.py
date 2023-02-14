#!/usr/bin/env python3

from http.server import HTTPServer, BaseHTTPRequestHandler
from http import HTTPStatus
import json
import time
import socket
import copy
from datetime import datetime


rsp_template = {
"APPROVAL_CODE":"TST00001",
"TXN_RESPONSE_CODE":"000",
"RRN":"RRN123456",
#"HOST_TIMESTAMP":"",
"HOST_TEXT":"Test approved!",
"CREDENTIALS_SCHEME_NAME":"tst-ursula",
"TXN_AMOUNT":"",
#"TXN_AMOUNT_IS_BALANCE":"",
#"AUX_USER_CREDENTIALS_VALUE":"",
#"AUX_USER_CREDENTIALS_TYPE":"",
}


def ursula_test_handler(req):
    rsp = copy.deepcopy(rsp_template)
    #rsp['TXN_AMOUNT'] = req['TXN_AMOUNT']
    #rsp['TXN_AMOUNT_IS_BALANCE'] = 'N'
    rsp['TXN_AMOUNT'] = '12800'
    rsp['TXN_AMOUNT_IS_BALANCE'] = 'Y'
    
    rsp['TXN_RESPONSE_CODE'] = '000'
    date_string = f'{datetime.now():%y%m%d%H%M%S}'
    rsp['HOST_TEXT'] = "Test approved @ " + date_string + '!'

    return rsp


class _RequestHandler(BaseHTTPRequestHandler):
    # Borrowing from https://gist.github.com/nitaku/10d0662536f37a087e1b
    def _set_headers(self):
        self.send_response(HTTPStatus.OK.value)
        self.send_header('Content-type', 'application/json')
        # Allow requests from any origin, so CORS policies don't
        # prevent local development.
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
    '''
    def do_GET(self):
        self._set_headers()
        self.wfile.write(json.dumps(_g_posts).encode('utf-8'))
    '''

    def do_POST(self):
        length = int(self.headers.get('content-length'))
        message = json.loads(self.rfile.read(length))
        #message['date_ms'] = int(time.time()) * 1000
        #_g_posts.append(message)
        ursula_rsp = ursula_test_handler(message)
        self._set_headers()
        #self.wfile.write(json.dumps({'success': True}).encode('utf-8'))
        self.wfile.write(json.dumps(ursula_rsp).encode('utf-8'))

    def do_OPTIONS(self):
        # Send allow-origin header for preflight POST XHRs.
        self.send_response(HTTPStatus.NO_CONTENT.value)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST')
        self.send_header('Access-Control-Allow-Headers', 'content-type')
        self.end_headers()

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


def run_server():
    def_ip = get_ip()
    print("local ip is ", def_ip)
    server_address = (def_ip, 8080)
    print("starting up on %s port %s" % server_address)
    #server_address = ('', 8001)
    httpd = HTTPServer(server_address, _RequestHandler)
    print('serving at %s:%d' % server_address)
    httpd.serve_forever()


if __name__ == '__main__':
    run_server()
    