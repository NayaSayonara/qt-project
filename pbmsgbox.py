# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'pbmsgbox2.ui'
##
## Created by: Qt User Interface Compiler version 5.15.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *


class Ui_pbMessageBox(object):
    def setupUi(self, pbMessageBox):
        if not pbMessageBox.objectName():
            pbMessageBox.setObjectName(u"pbMessageBox")
        pbMessageBox.resize(600, 532)
        pbMessageBox.setModal(True)
        self.msgBoxText = QLabel(pbMessageBox)
        self.msgBoxText.setObjectName(u"msgBoxText")
        self.msgBoxText.setGeometry(QRect(10, 10, 571, 281))
        font = QFont()
        font.setFamily(u"Berlin Sans FB")
        font.setPointSize(36)
        self.msgBoxText.setFont(font)
        self.msgBoxText.setAlignment(Qt.AlignBottom|Qt.AlignHCenter)
        self.msgBoxText.setWordWrap(True)
        self.msgBoxImage = QLabel(pbMessageBox)
        self.msgBoxImage.setObjectName(u"msgBoxImage")
        self.msgBoxImage.setGeometry(QRect(10, 290, 571, 231))
        self.msgBoxImage.setFont(font)
        self.msgBoxImage.setScaledContents(True)
        self.msgBoxImage.setAlignment(Qt.AlignCenter)
        self.msgBoxImage.setWordWrap(True)

        self.retranslateUi(pbMessageBox)

        QMetaObject.connectSlotsByName(pbMessageBox)
    # setupUi

    def retranslateUi(self, pbMessageBox):
        pbMessageBox.setWindowTitle(QCoreApplication.translate("pbMessageBox", u"Dialog", None))
        self.msgBoxText.setText(QCoreApplication.translate("pbMessageBox", u"TextLabel", None))
        self.msgBoxImage.setText("")
    # retranslateUi

