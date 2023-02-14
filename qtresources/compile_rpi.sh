echo "RPi Compiling UI files..."
# this must be run on RPi to match the resource version
pyside2-rcc paybox.qrc > paybox_rc.py
cp -v paybox_rc.py ../
echo "... done!"
