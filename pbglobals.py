'''
qrc file must be compiled on RPi!
ui file must be compiled on Ubuntu18!


fixed 'coin for notes' change scheme:

100 CZK - full coin exchange
200 CZK - full coin exchange

'prefer 200 CZK notes' approach:
500 CZK - 300 CZK coin exchange, notes: 2*100 or 200 change
1000 CZK - (a) 200 CZK or (b) 400 CZK coin exchange, change 800 CZK or 600 CZK (do we really need option (b)??)

2000, 5000 CZK - no acceptance


receipts for cash operations? (for fiscalisation etc)?
qr code receipts? printer? ursula links?

no direct receipts in case of vendotek (vs valina)

card 500 CZK with 400 CZK credit:
activate (no payment) or topup (say, 100 CZK with final balance 100+400)?

'''


# global vars definition

app_version = '0.6.10914'


currentBalance = 0
sessionBalance = 0
exchangeBalance = 0

cardPAN = ''

currency = 'CZK'
currency2 = 'CZ'


minExchangeAmount = 10000
adjExchangeAmountFine = 10000
adjExchangeAmountCoarse = 20000

fixedExchangeScheme = True
flexible1000Exchange = True
coinsFor100 = 10000
coinsFor200 = 20000
coinsFor500 = 30000
# minimum coins if flexible exchange
coinsFor1000 = 20000
# second option for coin amt if flexible exchange, must be greater than coinsFor1000
coinsFor1000Alt = 40000
# price for a new Vtek card
cardPrice = 50000
cardInitialBalance = 40000

hopper_min_delay_time = 0.06
hopper_poll_delay_time = 0.2
bnv_min_delay_time = 0.06
bnv_poll_delay_time = 0.2

hopper_cc2_address = 7
bnv_cc2_address = 40
# retries if no answer or 'busy'
cc2_cmd_retries = 5
cc2_cmd_retry_delay = 0.8

shortTO = 0.5
longTO = 20
sessionTO = 120
note_collect_timeout = 20.5
back_to_main_page_timeout = 60.5

bnv_rc_denom1_value = 10000
bnv_rc_denom2_value = 20000


cdSTX = b'\x02'
cdETX = b'\x03'
cdOK = 'Y'
cdNOK = 'N'

cd_cmd_retries = 3
cd_cmd_retry_delay = 0.5

ini_file_name = ''
ini_file_name_default = './paybox.ini'


# global/singleton instances
ev_shutdown = None

qt_quit = False
qt_ui_inhibit = False
qt_app = None
qt_win = None

qt_btn1_state_hopper_active = None
qt_btn1_state_bnv_active = None
qt_btn1_state_cd_active = None

gui2sm_queue = None
sm2gui_queue = None
coreSMT = None
dbg_quit = False
gp_link_up = False
logger = None
start_time = None
ursula_link_up = False

hopperInstance = None
bnvInstance = None
cdInstance = None
nfcInstance = None
# ursula txn uploader instance
ursulaInstance = None

pbConfig = None
