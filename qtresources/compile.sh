echo "Compiling UI files..."
pyside2-uic paybox6.ui > ui_paybox.py
cp -v ui_paybox.py ../ui_paybox.py
pyside2-uic pbmsgbox2.ui > pbmsgbox2.py
cp -v pbmsgbox2.py ../pbmsgbox.py
# this must be run on RPi to match the resource version
# pyside2-rcc paybox.qrc > paybox_rc.py
echo "... done!"
