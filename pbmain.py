from logprint import print

import sys
import traceback
import signal

from PySide2.QtWidgets import QApplication, QMainWindow, QDialog
from PySide2 import QtCore, QtWidgets
from PySide2 import QtGui
from PySide2.QtCore import QFile, QTimer
from PySide2.QtGui import QMovie

from ui_paybox import Ui_MainWindow
from pbmsgbox import Ui_pbMessageBox

import queue
import time

import pbglobals as pbg
import pbcore as pbc
from utils import *
from pbtranslator import CoreTranslator, get_ui_cmd_template
from trackedobject import TrackedObject
from pbce import CustomException
import qrcode

class MessageBox(QDialog, Ui_pbMessageBox):
    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        self.setupUi(self)


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.fontDB = QtGui.QFontDatabase()
        self.fontDB.addApplicationFont(":/fonts/BRLNSR.TTF")
        
        self.setupUi(self)
        
        self.cfntext = self.i0lblGetCoins.text()
        self.cdfntext = self.i0lblNewCard.text()
        self.tufntext = self.i0lblRechargeCard.text()
        self.cdbtext = self.i0lblCardBalance.text()
        
        self.userChoice = ''
        self.cur_cmd_result = None
        
        pbg.qt_ui_inhibit = True
    
        self.setFixedWidth(1024)
        self.setFixedHeight(768)
        
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.FramelessWindowHint | QtCore.Qt.MaximizeUsingFullscreenGeometryHint)
        self.connectButtons()
        
        #self.setMainPage()
        
        #self.showFullScreen()
        ##self.showMaximized()    
        
        self.setCursor(QtCore.Qt.BlankCursor)
        # Show mouse cursor (parent's cursor is used)
        #self.unsetCursor()
        #QApplication::setOverrideCursor(cursor);
        #QApplication::changeOverrideCursor(cursor);
        
        #self._message_box = QtWidgets.QMessageBox()
        self._message_box = MessageBox(self)
        self._message_box_shown = False
        
        # translator thread works with qt gui via Signal functionality
        self.translator_queue = queue.Queue()
        self.thread = QtCore.QThread()
        self.worker = CoreTranslator(self.translator_queue)

        self.worker.moveToThread(self.thread)
        
        self.thread.started.connect(self.worker.translatorWorker)
        
        self.worker.result_ready.connect(self.thread.quit)
        self.worker.result_ready.connect(self.worker.deleteLater)
        
        #self.thread.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.result_ready.connect(self.process_result)
        
        self.thread.start()
        print('translator thread scheduled')

        self.mainPageTimer = QTimer()
        self.mainPageTimer.timeout.connect(self.timeoutToMainPage)

        self.setMainPage()
        
    def timeoutToMainPage(self):
        print('timeoutToMainPage')
        self.mainPageTimer.stop()
        self.setMainPage()
    
    def keyPressEvent(self, event):
        key_pressed = event.key()
        print('pressed', key_pressed)
        #if key_pressed == QtCore.Qt.Key_Escape:
        #    self.close()
            
    def keyReleaseEvent(self, event):
        key_released = event.key()
        print('released', key_released)
        if key_released == QtCore.Qt.Key_Escape and not event.isAutoRepeat():
            print('true released', key_released)
            self.close()
        elif event.isAutoRepeat():
            print('auto released', key_released)
        
    def connectButtons(self):
        self.i0btnQuit.clicked.connect(self.slotBtnQuit)
        self.i0btnGetCoins.clicked.connect(self.coinsForNotes)
        self.i0btnNewCard.clicked.connect(self.cardForNotes)
        self.i0btnRechargeCard.clicked.connect(self.topupForNotes)
        self.i0btnCardBalance.clicked.connect(self.cardBalance)
        
        self.i1btnBack.clicked.connect(self.backMainPage)
        self.i3btnDismiss.clicked.connect(self.setMainPage)
        
        self.i1btnNext.clicked.connect(self.insertNotesNextPressed)
        
        if pbg.fixedExchangeScheme:
            #self.i1btnNext.clicked.connect(self.setFixedExchangePage)
            self.i4btnExBack.clicked.connect(self.backInsertNotesPage)
            self.i4btnExChoice1.clicked.connect(self.getCoins1000)
            self.i4btnExChoice2.clicked.connect(self.getCoins1000Alt)
        else:
            #self.i1btnNext.clicked.connect(self.setFlexExchangePage)
            self.i2btnExDone.clicked.connect(self.getCoinsExec)
            self.i2btnExBack.clicked.connect(self.backInsertNotesPage)
            self.i2btnExAdd100.clicked.connect(self.incExBalance100)
            self.i2btnExAdd10.clicked.connect(self.incExBalance10)
            self.i2btnExSub100.clicked.connect(self.decExBalance100)
            self.i2btnExSub10.clicked.connect(self.decExBalance10)
        
    def setMainPage(self):
        print('setMainPage')
        self.initNewSession()
        self.stackedWidget.setCurrentWidget(self.i0mainPage)
        self.refreshButtons()
        # set qmovie as label
        self.movie = QMovie("carwash.gif")
        self.i0lblAnimated.setMovie(self.movie)
        self.movie.start()
        
        if pbg.qt_ui_inhibit:
            self.pleaseWait('Service suspended, Please Wait...')
        else:
            if self._message_box_shown:
                self._message_box.accept()
                self._message_box_shown = False
        
    def refreshButtons(self):
        # explicit reads for each tracked var so that 'value_changed' is reset
        cfnbtn1 = pbg.qt_btn1_state_hopper_active.value
        cfnbtn2 = pbg.qt_btn1_state_bnv_active.value
        cfnbtn3 = pbg.qt_btn1_state_cd_active.value

        cfnbtn = cfnbtn1 and cfnbtn2
        self.i0btnGetCoins.setEnabled(cfnbtn)
        if cfnbtn:
            self.i0lblGetCoins.setText(self.cfntext)
        else:
            self.i0lblGetCoins.setText('Sorry, not Available')

        cdfnbtn = cfnbtn2 and cfnbtn3
        self.i0btnNewCard.setEnabled(cdfnbtn)
        if cdfnbtn:
            self.i0lblNewCard.setText(self.cdfntext)
        else:
            self.i0lblNewCard.setText('Sorry, not Available')
        
        tufnbtn = cfnbtn2 and cfnbtn3
        self.i0btnRechargeCard.setEnabled(tufnbtn)
        if tufnbtn:
            self.i0lblRechargeCard.setText(self.tufntext)
        else:
            self.i0lblRechargeCard.setText('Sorry, not Available')
        
        print("btn state updated")

    def initNewSession(self):
        pbg.currentBalance = 0
        pbg.exchangeBalance = 0
        pbg.sessionBalance = 0
        
        pbg.cardPAN = ''
        
        if self.userChoice == 'coins_for_notes':
            ui_cmd = get_ui_cmd_template('coins_for_notes_accept_notes_stop')
            self.translator_queue.put(ui_cmd)
        elif self.userChoice == 'card_for_notes':
            ui_cmd = get_ui_cmd_template('card_for_notes_accept_notes_stop')
            self.translator_queue.put(ui_cmd)
        else:
            print("user choice not set", logl='warning')
        
        self.userChoice = ''
        

    def backMainPage(self):
        if pbg.sessionBalance + pbg.currentBalance == 0:
            self.setMainPage()
    
    def coinsForNotes(self):
        self.userChoice = 'coins_for_notes'
        text1 = pbg.currency + '100 - Full Exchange\n'
        text1 += pbg.currency + '200 - Full Exchange\n'
        text1 += pbg.currency + '500 - Full Exchange\n'
        text1 += pbg.currency + '1000 - Change ' + dot_amt(str(pbg.coinsFor1000)) + ' or ' + dot_amt(str(pbg.coinsFor1000Alt))
        text2 = pbg.currency + '2000, ' + pbg.currency + '5000 -\nNot Accepted\n\n\n'
        self.i1lblHelpMsg1.setText(text1)
        self.i1lblHelpMsg2.setText(text2)
        self.setInsertNotesPage()
        
    def cardForNotes(self):
        self.userChoice = 'card_for_notes'
        text1 = 'Card costs ' + pbg.currency + dot_amt(str(pbg.cardPrice)) + '\n\n'
        text1 += 'After Card activation your balance will be ' + pbg.currency + dot_amt(str(pbg.cardInitialBalance)) + ' +\n'
        text1 += 'any extra amount in excess of Card price\n'
        text1 += 'at a discounted rate, no change is given.'
        #text2 = 'No change is given\n'
        text2 = ''
        text2 += 'Please make sure you\nfollow all activation steps!\n'
        text2 += 'For more Info refer to T&C'
        self.i1lblHelpMsg1.setText(text1)
        self.i1lblHelpMsg2.setText(text2)
        self.setInsertNotesPage()
        
    def topupForNotes(self):
        # here insert notes is not the first step
        # user must present the card first (better for recovery)
        # also no change is given!
        self.userChoice = 'topup_for_notes'
        self.setCardInteractPage()
        
    def cardBalance(self):
        self.userChoice = 'card_balance'
        self.setCardInteractPage()
        
    def backInsertNotesPage(self):
        pbg.sessionBalance += pbg.currentBalance
        pbg.currentBalance = 0
        self.setInsertNotesPage()
        
    def setInsertNotesPage(self):
        ''' available notes
            100, 200, 500, 1000, 2000, 5000
        '''
        print('setInsertNotesPage')
        self.stackedWidget.setCurrentWidget(self.i1pageInsertNotes)
        
        self.i1lblCurrency.setText(pbg.currency)
        self.i1currentBalance.display(dot_amt(str(pbg.sessionBalance + pbg.currentBalance)))
        if pbg.sessionBalance + pbg.currentBalance > 0:
            self.i1btnNext.setEnabled(True)
            # No REFUNDS!!!
            self.i1btnBack.setEnabled(False)
        else:
            self.i1btnNext.setEnabled(False)
            self.i1btnBack.setEnabled(True)
            
        if self.userChoice == 'coins_for_notes':
            ui_cmd = get_ui_cmd_template('coins_for_notes_accept_notes_start')
            self.translator_queue.put(ui_cmd)
        elif self.userChoice == 'card_for_notes':
            ui_cmd = get_ui_cmd_template('card_for_notes_accept_notes_start')
            self.translator_queue.put(ui_cmd)
        elif self.userChoice == 'topup_for_notes':
            # reuse cmd as same policies
            ui_cmd = get_ui_cmd_template('card_for_notes_accept_notes_start')
            self.translator_queue.put(ui_cmd)
        else:
            print("user choice not set", logl='error')

    def insertNotesNextPressed(self):
        print('insertNotesNextPressed')
        if self.userChoice == 'coins_for_notes':
            if pbg.fixedExchangeScheme:
                self.setFixedExchangePage()
            else:
                self.setFlexExchangePage()
        elif self.userChoice == 'card_for_notes':
            ui_cmd = get_ui_cmd_template('card_for_notes_accept_notes_stop')
            self.translator_queue.put(ui_cmd)
            #self.setCardInteractPage()
        elif self.userChoice == 'topup_for_notes':
            # reuse cmd as same policies
            ui_cmd = get_ui_cmd_template('card_for_notes_accept_notes_stop')
            self.translator_queue.put(ui_cmd)

        else:
            print("user choice not set", logl='warning')
        

    def setFlexExchangePage(self):
        print('setFlexExchangePage')
        pbg.exchangeBalance = pbg.sessionBalance + pbg.currentBalance
        
        self.stackedWidget.setCurrentWidget(self.i2pageFlexExchange)
        
        self.i2lblExCurrency1.setText(pbg.currency)
        self.i2lblExCurrency2.setText(pbg.currency)
        
        self.i2btnExSub100.setText('-' + str(int(pbg.adjExchangeAmountCoarse/100)))
        self.i2btnExSub10.setText('-' + str(int(pbg.adjExchangeAmountFine/100)))
        self.i2btnExAdd100.setText('+' + str(int(pbg.adjExchangeAmountCoarse/100)))
        self.i2btnExAdd10.setText('+' + str(int(pbg.adjExchangeAmountFine/100)))
        
        self.i2lblCurBalance.setText(dot_amt(str(pbg.sessionBalance + pbg.currentBalance)))
        self.i2exchangeBalance.display(dot_amt(str(pbg.exchangeBalance)))
        
        if self.userChoice == 'coins_for_notes':
            ui_cmd = get_ui_cmd_template('coins_for_notes_accept_notes_stop')
            self.translator_queue.put(ui_cmd)
        elif self.userChoice == 'card_for_notes':
            ui_cmd = get_ui_cmd_template('card_for_notes_accept_notes_stop')
            self.translator_queue.put(ui_cmd)
        else:
            print("user choice not set", logl='error')

    def setFixedExchangePage(self):
        print('setFixedExchangePage')
        pbg.exchangeBalance = pbg.sessionBalance + pbg.currentBalance
        
        self.stackedWidget.setCurrentWidget(self.i4pageFixedExchange)
        self.i4lblExCurrency.setText(pbg.currency)
        
        self.i4btnExChoice1.setText(str(int(pbg.coinsFor1000/100)))
        self.i4btnExChoice2.setText(str(int(pbg.coinsFor1000Alt/100)))
        
        self.i4lblCurBalance.setText(dot_amt(str(pbg.sessionBalance + pbg.currentBalance)))
        
        if self.userChoice == 'coins_for_notes':
            ui_cmd = get_ui_cmd_template('coins_for_notes_accept_notes_stop')
            self.translator_queue.put(ui_cmd)
        elif self.userChoice == 'card_for_notes':
            ui_cmd = get_ui_cmd_template('card_for_notes_accept_notes_stop')
            self.translator_queue.put(ui_cmd)
        else:
            print("user choice not set", logl='error')

    def setTxnStatusPage(self):
        print('setTxnStatusPage')
        self.stackedWidget.setCurrentWidget(self.i3pageTxnStatus)
        
        self.mainPageTimer.start(pbg.back_to_main_page_timeout * 1000)
        
        if self.cur_cmd_result['status'] == 'complete':
            if self.cur_cmd_result['result'] == 'failure':
                self.i3lblTxnStatusIcon.setPixmap(QtGui.QPixmap(u":/bckgrnd/icn512nok.png"))
                self.i3lblTxnStatusIcon.setScaledContents(True)
                
                self.i3lblTxnStatusMsg1.setText('Sorry we could not\ncomplete this transaction')
                self.i3lblTxnStatusMsg2.setText('Please scan this QR-code\nand call Helpdesk')
            elif self.cur_cmd_result['result'] == 'success':
                self.i3lblTxnStatusIcon.setPixmap(QtGui.QPixmap(u":/bckgrnd/icn200approved.png"))
                self.i3lblTxnStatusIcon.setScaledContents(True)
                
                self.i3lblTxnStatusMsg1.setText('Transaction completed\nThank you!')
                self.i3lblTxnStatusMsg2.setText('Please scan this QR-code\nto view your receipt')
            else:
                print("bug: txn result must be success or failure", logl='error')
        else:
            print("bug: txn status must be complete", logl='error')

        if 'qr' in self.cur_cmd_result:
            #qr = qrcode.Qrcode('www.google.com')
            qr = qrcode.Qrcode(self.cur_cmd_result['qr'])
            pixmap = QtGui.QPixmap()
            pixmap.loadFromData(qr.render2ram(), 'png')
            #self.i3lblTxnQRcode.setPixmap(QtGui.QPixmap(u":/bckgrnd/qrcode-placeholder.png"))
            self.i3lblTxnQRcode.setPixmap(pixmap)

    def setCardInteractPage(self):
        print('setCardInteractPage')
        self.stackedWidget.setCurrentWidget(self.i5pageCardInteract)
        
        if self.userChoice == 'card_for_notes':
            self.i5lblCardMsg1.setText('Your Card is being dispensed')
            self.i5lblCardMsg2.setText('Pick up your Card and present it to the Reader')
            self.i5lblDismiss.setText('')
            self.i5btnDismiss.setEnabled(False)
            # dispense card and then read it
            ui_cmd = get_ui_cmd_template('card_for_notes_dispense_and_read_card')
            ui_cmd['customer_balance'] = pbg.sessionBalance + pbg.currentBalance - pbg.cardInitialBalance
            ui_cmd['notes'] = pbg.sessionBalance + pbg.currentBalance
            self.translator_queue.put(ui_cmd)

        elif self.userChoice == 'topup_for_notes':
            self.i5lblCardMsg1.setText('Please present Your Card to the Reader')
            self.i5lblCardMsg2.setText('')
            self.i5lblDismiss.setText('Back')
            self.i5btnDismiss.setText('X')
            self.i5btnDismiss.setEnabled(True)
            ui_cmd = get_ui_cmd_template('topup_for_notes_read_card')
            self.translator_queue.put(ui_cmd)
            
        elif self.userChoice == 'card_balance':
            self.i5lblCardMsg1.setText('Please present Your Card to the Reader')
            self.i5lblCardMsg2.setText('')
            self.i5lblDismiss.setText('Back')
            self.i5btnDismiss.setText('X')
            self.i5btnDismiss.setEnabled(True)
            ui_cmd = get_ui_cmd_template('card_balance_read_card')
            self.translator_queue.put(ui_cmd)
            
        else:
            print("user choice not set", logl='error')


    def slotBtnQuit(self):
        self.qtQuit()
        
    def qtQuit(self):
        print('Exiting')
        
        if self._message_box_shown:
            self._message_box.accept()
            self._message_box_shown = False
            
        ui_cmd = get_ui_cmd_template('quit')
        self.translator_queue.put(ui_cmd)
        self.thread.quit()
        self.thread.wait()
        self.close()
        
    def incExBalance100(self):
        amt = pbg.adjExchangeAmountCoarse
        delta = pbg.sessionBalance + pbg.currentBalance - pbg.exchangeBalance
        if delta >= amt:
            pbg.exchangeBalance += amt
        else:
            pbg.exchangeBalance += delta
        self.i2exchangeBalance.display(dot_amt(str(pbg.exchangeBalance)))
        
    def incExBalance10(self):
        amt = pbg.adjExchangeAmountFine
        delta = pbg.sessionBalance + pbg.currentBalance - pbg.exchangeBalance
        if delta >= amt:
            pbg.exchangeBalance += amt
        else:
            pbg.exchangeBalance += delta
        self.i2exchangeBalance.display(dot_amt(str(pbg.exchangeBalance)))
        
    def decExBalance100(self):
        amt = pbg.adjExchangeAmountCoarse
        min_amt = pbg.minExchangeAmount
        delta = pbg.exchangeBalance - amt
        if delta >= min_amt:
            pbg.exchangeBalance -= amt
        else:
            pbg.exchangeBalance = min_amt
        self.i2exchangeBalance.display(dot_amt(str(pbg.exchangeBalance)))
        
    def decExBalance10(self):
        amt = pbg.adjExchangeAmountFine
        min_amt = pbg.minExchangeAmount
        delta = pbg.exchangeBalance - amt
        if delta >= min_amt:
            pbg.exchangeBalance -= amt
        else:
            pbg.exchangeBalance = min_amt
        self.i2exchangeBalance.display(dot_amt(str(pbg.exchangeBalance)))
        
    def getCoins1000(self):
        pbg.exchangeBalance = pbg.coinsFor1000
        self.getCoinsExec()
        
    def getCoins1000Alt(self):
        pbg.exchangeBalance = pbg.coinsFor1000Alt
        self.getCoinsExec()
    
    def getCoinsExec(self):
        if pbg.fixedExchangeScheme:
            customerBalance = pbg.sessionBalance + pbg.currentBalance
            if customerBalance == 10000:
                pbg.exchangeBalance = pbg.coinsFor100
            elif customerBalance == 20000:
                pbg.exchangeBalance = pbg.coinsFor200
            elif customerBalance == 50000:
                pbg.exchangeBalance = pbg.coinsFor500
            elif customerBalance == 100000:
                #pbg.exchangeBalance = pbg.coinsFor1000
                pass
            else:
                print('Unexpected customer balance value', customerBalance, logl='error')
                pbg.exchangeBalance = customerBalance

        print('Customer balance', pbg.sessionBalance + pbg.currentBalance)
        print('Hopper will dispense', pbg.exchangeBalance)
        print('Bill Validator will return', pbg.sessionBalance + pbg.currentBalance - pbg.exchangeBalance)

        ui_cmd = get_ui_cmd_template('coins_for_notes')
        #ui_cmd['coins'] = pbg.exchangeBalance
        # debug!
        ui_cmd['coins'] = pbg.exchangeBalance // 500
        ui_cmd['notes'] = pbg.sessionBalance + pbg.currentBalance - pbg.exchangeBalance
        ui_cmd['customer_balance'] = pbg.sessionBalance + pbg.currentBalance
        self.translator_queue.put(ui_cmd)
        self.pleaseWait('Processing Now, Please Wait...')
        
    def getCardExec(self):
        print('Customer balance', pbg.sessionBalance + pbg.currentBalance)
        #print('Bill Validator will return', pbg.sessionBalance + pbg.currentBalance - pbg.cardPrice)

        ui_cmd = get_ui_cmd_template('card_for_notes')
        #ui_cmd['notes'] = pbg.sessionBalance + pbg.currentBalance - pbg.cardPrice
        #ui_cmd['customer_balance'] = pbg.sessionBalance + pbg.currentBalance
        ui_cmd['customer_balance'] = pbg.sessionBalance + pbg.currentBalance - pbg.cardInitialBalance
        ui_cmd['notes'] = pbg.sessionBalance + pbg.currentBalance
        ui_cmd['credentials_value'] = pbg.cardPAN
        #if 'credentials_value' in self.cur_cmd_result:
        #    ui_cmd['credentials_value'] = self.cur_cmd_result['credentials_value']
            
        
        self.translator_queue.put(ui_cmd)
        #self.pleaseWait('Processing Now, Please Wait...')
        
    def topupExec(self):
        print('Customer balance', pbg.sessionBalance + pbg.currentBalance)
        
        # reuse card_for_notes cmd for ursula comms
        ui_cmd = get_ui_cmd_template('card_for_notes')
        ui_cmd['customer_balance'] = pbg.sessionBalance + pbg.currentBalance
        ui_cmd['notes'] = pbg.sessionBalance + pbg.currentBalance
        ui_cmd['credentials_value'] = pbg.cardPAN
        #if 'credentials_value' in self.cur_cmd_result:
        #    ui_cmd['credentials_value'] = self.cur_cmd_result['credentials_value']
        
        self.translator_queue.put(ui_cmd)
        
    def pleaseWait(self, text):
        print("entered pleaseWait")
        #self._message_box.setText(text)
        self._message_box.msgBoxText.setText(text)
        
        # optional image
        #self._message_box.msgBoxImage.setPixmap(QtGui.QPixmap(u":/bckgrnd/Logo_mobivend.png"))
        #self._message_box.msgBoxImage.setScaledContents(False)
        
        #self._message_box.setStandardButtons(QtWidgets.QMessageBox.NoButton)
        self._message_box.setWindowFlags(self.windowFlags() | QtCore.Qt.FramelessWindowHint)
        #self._message_box.setFixedSize(400, 300)
        self._message_box.setFixedSize(600, 400)
        self._message_box.move(300, 200)
        self._message_box.show()
        self._message_box_shown = True
        
    def process_result(self, result):
        print("process_result received", result)
        
        self.cur_cmd_result = result

        if result['command'] == 'quit':
            #self.close()
            self.qtQuit()
            
        elif result['command'] == 'coins_for_notes':
            if result['status'] != 'complete':
                if self._message_box_shown:
                    joinedText = result['message_hopper'] + '\n' + result['message_bnv']
                    self._message_box.msgBoxText.setText(joinedText)
            else:
                if self._message_box_shown:
                    self._message_box.accept()
                    self._message_box_shown = False

                self.setTxnStatusPage()
                
        elif result['command'] == 'card_for_notes':
            if result['status'] != 'complete':
                if self._message_box_shown:
                    joinedText = result['message_cd'] + '\n' + result['message_bnv']
                    self._message_box.msgBoxText.setText(joinedText)
            else:
                if self._message_box_shown:
                    self._message_box.accept()
                    self._message_box_shown = False

                self.setTxnStatusPage()
                
        elif result['command'] == 'card_for_notes_dispense_and_read_card':

            if result['result'] == 'popup_show':
                if not self._message_box_shown:
                    joinedText = result['message_cd'] + '\n' + result['message_nfc']
                    self.pleaseWait(joinedText)
                else:
                    joinedText = result['message_cd'] + '\n' + result['message_nfc']
                    self._message_box.msgBoxText.setText(joinedText)
            elif result['result'] == 'popup_hide':
                if self._message_box_shown:
                    self._message_box.accept()
                    self._message_box_shown = False

            if result['status'] != 'complete':
                if self._message_box_shown:
                    joinedText = result['message_cd'] + '\n' + result['message_nfc']
                    self._message_box.msgBoxText.setText(joinedText)
            else:
                if self._message_box_shown:
                    self._message_box.accept()
                    self._message_box_shown = False

                pbg.cardPAN = result['credentials_value']
                self.getCardExec()
                
        elif result['command'] == 'topup_for_notes_read_card':

            if result['result'] == 'failure' and result['status'] == 'complete':
                #self.setMainPage()
                self.setTxnStatusPage()
            else:
                pbg.cardPAN = result['credentials_value']
                
                text1 = 'Please note that no change\nwill be given'
                text2 = ''
                text2 += 'For more Info refer to T&C'
                self.i1lblHelpMsg1.setText(text1)
                self.i1lblHelpMsg2.setText(text2)
                self.setInsertNotesPage()
                
        elif result['command'] == 'card_balance_read_card':
            if result['result'] == 'failure' and result['status'] == 'complete':
                self.setMainPage()
            else:
                if result['status'] != 'complete':
                    if result['result'] == 'popup_show':
                        if not self._message_box_shown:
                            joinedText = result['message_nfc'] + '\n' + result['message_ursula']
                            self.pleaseWait(joinedText)
                        else:
                            joinedText = result['message_nfc'] + '\n' + result['message_ursula']
                            self._message_box.msgBoxText.setText(joinedText)
                    elif result['result'] == 'popup_hide':
                        if self._message_box_shown:
                            self._message_box.accept()
                            self._message_box_shown = False
                else:
                    if self._message_box_shown:
                        self._message_box.accept()
                        self._message_box_shown = False

                    self.setMainPage()
            
        elif result['command'] == 'coins_for_notes_accept_notes_start':
            if result['result'] == 'failure' and result['status'] == 'complete':
                self.setMainPage()
            else:
                pbg.currentBalance = result['customer_balance']
                self.i1currentBalance.display(dot_amt(str(pbg.sessionBalance + pbg.currentBalance)))
                
                if result['result'] == 'popup_show':
                    if not self._message_box_shown:
                        self.pleaseWait(result['message_bnv'])
                    else:
                        #joinedText = result['message_hopper'] + '\n' + result['message_bnv']
                        joinedText = result['message_bnv']
                        self._message_box.msgBoxText.setText(joinedText)
                elif result['result'] == 'popup_hide':
                    if self._message_box_shown:
                        self._message_box.accept()
                        self._message_box_shown = False
                        
                if pbg.fixedExchangeScheme:
                    if pbg.flexible1000Exchange and pbg.sessionBalance + pbg.currentBalance >= 100000:
                        # either full adjustment ot choice of 2 buttons (tbc)
                        #self.setFlexExchangePage()
                        self.setFixedExchangePage()
                    else:
                        # straight to exchange
                        if pbg.sessionBalance + pbg.currentBalance > 0:
                            ui_cmd = get_ui_cmd_template('coins_for_notes_accept_notes_stop')
                            self.translator_queue.put(ui_cmd)
                else:
                    if pbg.sessionBalance + pbg.currentBalance > 0:
                        self.i1btnNext.setEnabled(True)
                    else:
                        self.i1btnNext.setEnabled(False)
            
        elif result['command'] == 'card_for_notes_accept_notes_start':
        
            if result['result'] == 'failure' and result['status'] == 'complete':
                # todo check if need qr for bad status
                if 'customer_balance' in result:
                    failure_balance = result['customer_balance']
                else:
                    failure_balance = 0
                if failure_balance + pbg.sessionBalance + pbg.currentBalance > 0:
                    self.setTxnStatusPage()
                else:
                    self.setMainPage()
            else:
                pbg.currentBalance = result['customer_balance']
                self.i1currentBalance.display(dot_amt(str(pbg.sessionBalance + pbg.currentBalance)))
                
                if self.userChoice == 'card_for_notes':
                    if pbg.sessionBalance + pbg.currentBalance >= pbg.cardPrice:
                        self.i1btnNext.setEnabled(True)
                    else:
                        self.i1btnNext.setEnabled(False)
                elif self.userChoice == 'topup_for_notes':
                    # any amt is good for topup
                    if pbg.sessionBalance + pbg.currentBalance > 0:
                        self.i1btnNext.setEnabled(True)
                    else:
                        self.i1btnNext.setEnabled(False)
                else:
                    print("unexpected self.userChoice", self.userChoice, logl='warning')
                    
                if result['result'] == 'popup_show':
                    if not self._message_box_shown:
                        self.pleaseWait(result['message_bnv'])
                    else:
                        joinedText = result['message_bnv']
                        self._message_box.msgBoxText.setText(joinedText)
                elif result['result'] == 'popup_hide':
                    if self._message_box_shown:
                        self._message_box.accept()
                        self._message_box_shown = False
                        
            
        elif result['command'] == 'coins_for_notes_accept_notes_stop':
            pbg.currentBalance = result['customer_balance']
            self.i1currentBalance.display(dot_amt(str(pbg.sessionBalance + pbg.currentBalance)))

            if pbg.fixedExchangeScheme:
                if pbg.sessionBalance + pbg.currentBalance > 0:
                    if pbg.flexible1000Exchange and pbg.sessionBalance + pbg.currentBalance >= 100000:
                        print("flexible1000Exchange - stay on adjust exchange balance page")
                        pass
                    else:
                        self.getCoinsExec()

        elif result['command'] == 'card_for_notes_accept_notes_stop':
            pbg.currentBalance = result['customer_balance']
            self.i1currentBalance.display(dot_amt(str(pbg.sessionBalance + pbg.currentBalance)))
            
            if self.userChoice == 'card_for_notes':
                self.setCardInteractPage()
            elif self.userChoice == 'topup_for_notes':
                # todo complete txn
                if result['status'] != 'complete':
                    if self._message_box_shown:
                        joinedText = result['message_cd'] + '\n' + result['message_bnv']
                        self._message_box.msgBoxText.setText(joinedText)
                else:
                    if self._message_box_shown:
                        self._message_box.accept()
                        self._message_box_shown = False

                    self.topupExec()
                    self.setTxnStatusPage()
            else:
                print("unexpected self.userChoice", self.userChoice, logl='warning')

        else:
            print("no case for this cmd")
            pass
                
        print("process_result finished")
        

def sig_handler(*args):
    raise CustomException('got SIGTERM, shutting down')

def excepthook(exc_type, exc_value, exc_tb):
    tb = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    print("exception caught", logl='error')
    print("exception info: ", tb, logl='error')
    pbg.qt_quit = True

sys.excepthook = excepthook
    
    
def qtPoller():
    # test ui blocking
    if pbg.qt_ui_inhibit:
        if time.time() - pbg.start_time > 15.3:
            pbg.qt_ui_inhibit = False
            pbg.qt_win.mainPageTimer.start(200)
            print("qt ui unblocked")

    if pbg.qt_quit:
        pbg.qt_quit = False
        print("initiate qt shutdown")
        pbg.qt_win.qtQuit()
        
    if pbg.qt_btn1_state_hopper_active.value_changed or pbg.qt_btn1_state_bnv_active.value_changed or pbg.qt_btn1_state_cd_active.value_changed:
        print("btn state changed")
        pbg.qt_win.refreshButtons()
        pbg.qt_win.update()
    
    
def main():
    pbg.qt_app = QApplication(sys.argv)
    
    #signal.signal(signal.SIGINT, sigint_handler)
    signal.signal(signal.SIGTERM, sig_handler)
    
    pbg.qt_btn1_state_hopper_active = TrackedObject(False)
    pbg.qt_btn1_state_bnv_active = TrackedObject(False)
    pbg.qt_btn1_state_cd_active = TrackedObject(True)
    
    timer = QTimer()
    timer.timeout.connect(lambda: qtPoller())
    timer.start(250)

    pbc.coreMain()
    
    pbg.qt_win = MainWindow()
    pbg.qt_win.show()

    qt_rc = pbg.qt_app.exec_()
    print('qt app finished with code ', qt_rc)
    
    # ensure correct deletion order
    del pbg.qt_win, pbg.qt_app
    
        
if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, SystemExit):
        if pbg.logger is not None:
            pbg.logger.info("coreMain KeyboardInterrupt or SystemExit")
        else:
            raise
    except Exception as e:
        if pbg.logger is not None:
            print("coreMain Caught EXCEPTION: %s", e)
            pbg.logger.exception("coreMain Caught EXCEPTION: %s", e)
        else:
            raise
    finally:
        print("coreMain shutting down...")
        pbc.coreShutdown()
        print("coreMain exited")
    
