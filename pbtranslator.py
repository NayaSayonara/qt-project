from logprint import print

import sys
from PySide2 import QtCore

import queue
import time
import copy

import pbglobals as pbg
#import pbcore as pbc
from utils import *


ui_commands = \
[
{
    # request
    'command': 'coins_for_notes',
    'coins': 0,
    'notes': 0,
    'customer_balance': 0,
    # response
    'result': 'unknown',
    'status': 'unknown',
    'message_hopper': '',
    'message_bnv': '',
    'qr': '',
},
{
    # request
    'command': 'coins_for_notes_end_session',
    # response
    'result': 'unknown',
    'status': 'unknown',
    'message': '',
},
{
    # request
    'command': 'coins_for_notes_accept_notes_start',
    # response
    'result': 'unknown',
    'status': 'unknown',
    'message': '',
    'customer_balance': 0,
},
{
    # request
    'command': 'coins_for_notes_accept_notes_stop',
    # response
    'result': 'unknown',
    'status': 'unknown',
    'message': '',
    'customer_balance': 0,
},

{
    # request
    'command': 'card_for_notes',
    'notes': 0,
    'customer_balance': 0,
    'credentials_type': 'PAN',
    'credentials_value': '',
    # response
    'result': 'unknown',
    'status': 'unknown',
    'message_cd': '',
    'message_bnv': '',
    'qr': '',
},
{
    # request
    'command': 'card_for_notes_dispense_and_read_card',
    'notes': 0,
    'customer_balance': 0,
    # response
    'result': 'unknown',
    'status': 'unknown',
    'message_cd': '',
    'message_nfc': '',
    'credentials_type': 'PAN',
    'credentials_value': '',
    'qr': '',
},
{
    # request
    'command': 'topup_for_notes_read_card',
    # response
    'result': 'unknown',
    'status': 'unknown',
    'message_nfc': '',
    'credentials_type': 'PAN',
    'credentials_value': '',
    'qr': '',
},
{
    # request
    'command': 'card_balance_read_card',
    # response
    'result': 'unknown',
    'status': 'unknown',
    'message_nfc': '',
    'message_ursula': '',
    'credentials_type': 'PAN',
    'credentials_value': '',
    'qr': '',
},
{
    # request
    'command': 'card_for_notes_end_session',
    # response
    'result': 'unknown',
    'status': 'unknown',
    'message': '',
},
{
    # request
    'command': 'card_for_notes_accept_notes_start',
    # response
    'result': 'unknown',
    'status': 'unknown',
    'message': '',
    'customer_balance': 0,
},
{
    # request
    'command': 'card_for_notes_accept_notes_stop',
    # response
    'result': 'unknown',
    'status': 'unknown',
    'message': '',
    'customer_balance': 0,
},

{
    # request
    'command': 'quit',
    # response
    'result': 'success',
    'status': 'complete',
},
]

def get_ui_cmd_template(cmd):
    for i in range(len(ui_commands)):
        ui_command = ui_commands[i]
        if ui_command['command'] == cmd:
            return copy.deepcopy(ui_command)

# translator thread works with qt gui via Signal functionality
# fetches data via Queue and emits result when ready (or progress made)
class CoreTranslator(QtCore.QObject):
    result_ready = QtCore.Signal(dict)
    
    def __init__(self, translator_queue):
        super(CoreTranslator, self).__init__()
        self.translator_queue = translator_queue
        self._ev_exit = pbg.ev_shutdown
    
    def translatorWorker(self):
        print('translator started')
        ui_cmd = None
        #ui_cmd_rsp = None
        while True:
            try:
                if not self.translator_queue.empty():
                    ui_cmd = self.translator_queue.get()
                    print("translator received", ui_cmd)
                    #ui_cmd_rsp = None
                    if ui_cmd['command'] == 'quit':
                        break
                    
                    # TODO reuse the same templates?
                    pbg.gui2sm_queue.put(ui_cmd)

                #if ui_cmd_rsp is None:
                if not pbg.sm2gui_queue.empty():
                    ui_cmd_rsp = pbg.sm2gui_queue.get()
                    
                    self.result_ready.emit(ui_cmd_rsp)

                time.sleep(0.2)
                
            except queue.Empty:
                if self._ev_exit.is_set():
                    print("translatorWorker got shutdown evt")
                    quit_cmd = get_ui_cmd_template('quit')
                    self.result_ready.emit(quit_cmd)
                    break
                continue
            
        print('translator thread done')

