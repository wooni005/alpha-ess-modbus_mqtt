#!/usr/bin/python3

import os
import sys
import signal
import termios
import time
import traceback
import socket
import fcntl
import errno


# external files/classes
import modbus

MOXA_TCP_PORT = 4004
MOXA_IP_ADDR = '192.168.5.225'

exitProgram = False
serialPort = None
oldSettings = None
MOXA_TCP_PORT = MOXA_TCP_PORT


def current_sec_time():
    return int(round(time.time()))


def current_milli_time():
    return int(round(time.time() * 1000))


def signal_handler(_signal, frame):
    global exitProgram

    print('You pressed Ctrl+C!')
    exitProgram = True


def initAnykey():
    global oldSettings

    oldSettings = termios.tcgetattr(sys.stdin)
    newSettings = termios.tcgetattr(sys.stdin)
    # newSettings[3] = newSettings[3] & ~(termios.ECHO | termios.ICANON)  # lflags
    newSettings[3] = newSettings[3] & ~(termios.ECHO | termios.ICANON)  # lflags
    newSettings[6][termios.VMIN] = 0  # cc
    newSettings[6][termios.VTIME] = 0  # cc
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, newSettings)


def restoreAnykey():
    global oldSettings
    if oldSettings:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, oldSettings)
        print("Old terminal settings restored")


def printHelp():
    print()
    print('Storion reader/terminal program')
    print()
    print('ESC or Ctrl-C: Exit program')
    print('1-Send request to Storion')
    print('h-Print this help')
    print()
    print('IP: %s PORT: %s' % (MOXA_IP_ADDR, moxaPortNr))
    print()


def printHexString(_str):
    for char in _str:
        print("%02X " % (ord(char)), end='')
    print()


def printHexByteString(_str):
    for v in _str:
        print("%02X " % v, end='')
    print()
    # print(" msg length: %d" % len(_str))


def sendModbusMsg(sendMsg, _modBusAddr):
    sendMsgList = list(sendMsg)
    sendMsgList[0] = chr(_modBusAddr)
    # print(sendMsgList)
    print("modBusAddr=%d" % _modBusAddr, end='')
    print(" -> send request to Storion T10: ", end='')
    sendMsg = ''
    for element in sendMsgList:
        # print("%02X " % ord(element), end='')
        sendMsg += element
    # printHexString(sendMsg)
    request = sendMsg + modbus.calculateCRC(sendMsg)
    printHexString(request)

    for char in request:
        sendByte = ord(char)
        # print("%02X " % sendByte, end='')
        sock.send(bytes([sendByte]), 1)
    # sock.send(request.encode('ascii'))


###
# Initalisation ####
###

# Init signal handler, because otherwise Ctrl-C does not work
signal.signal(signal.SIGINT, signal_handler)

# Make the following devices accessable for user
# os.system("sudo chmod 666 %s" % settings.serialPortDevice)

# Give Home Assistant and Mosquitto the time to startup
time.sleep(2)

masterMsg = "\x55\x03\x00\x00\x00\x0D"  # 0x89, 0xDB]

sendCrLf = False

if len(sys.argv) > 1:
    # Commandline arguments are given
    print("Port: %s" % (sys.argv[1]))
    moxaPortNr = int(sys.argv[1])
else:
    # Otherwise set default port nr
    moxaPortNr = MOXA_TCP_PORT

try:
    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Bind the socket to the port
    sock.connect((MOXA_IP_ADDR, moxaPortNr))

except Exception as arg:
    print("%s" % str(arg))
    traceback.print_exc()
    print("Program terminated.")
    sys.exit(1)

initAnykey()

fcntl.fcntl(sock, fcntl.F_SETFL, os.O_NONBLOCK)

powerCntAdd = 0
powerAvgAdd = 0

modBusAddr = 0x00
sendDelayTimer = 0
autoSend = False

printHelp()

try:
    while not exitProgram:
        if sendDelayTimer >= 2:
            sendDelayTimer = 0
            modBusAddr = modBusAddr + 1
            if modBusAddr >= 248:
                # modBusAddr = 1
                autoSend = False
            sendModbusMsg(masterMsg, modBusAddr)
            if not autoSend:
                print("Autosend stopped")

        ch = os.read(sys.stdin.fileno(), 1)
        if ch != b'':
            # Key is pressed
            if ch == b'\x1b':
                print("Escape pressed: Exit")
                exitProgram = True
            elif ch == b'r':
                print("Reset powerAvg")
                powerCntAdd = 0
                powerAvgAdd = 0
            elif ch == b'1':
                sendDelayTimer = 0
                sendModbusMsg(masterMsg, 0x55)
            if ch == b'2':
                if not autoSend:
                    print("Activate auto send")
                    autoSend = True
                else:
                    autoSend = False
                    modBusAddr = 1
            elif ch == b'h':
                printHelp()
            # else:
            #     print("%02X " % (ord(ch)), end='')
            #     sock.send(ch)
            #     sendCrLf = True
        else:
            if sendCrLf:
                sendCrLf = False
                print()

            try:
                recvMsg = sock.recv(100)
            except Exception as e:
                err = e.args[0]
                if err == errno.EAGAIN or err == errno.EWOULDBLOCK:
                    time.sleep(0.1)
                    if autoSend:
                        sendDelayTimer = sendDelayTimer + 1
                    # print('No data available')
                    continue
                else:
                    # a "real" error occurred
                    print(e)
                    exitProgram = True
            else:
                msgLen = len(recvMsg)
                print("Received msgLen: %d msg: " % msgLen, end='')
                printHexByteString(recvMsg)
                autoSend = False

                if msgLen == 8:
                    pass  # Ignore msg
                #     # Register get request from Storion to ACR10
                    # print(" 8: ", end='')
                    # for x in recvMsg:
                    #     print("%02X " % x, end='')
                    # print()
                #     print(" msg length: %d" % len(recvMsg))
                elif msgLen == 21:
                    pass  # Ignore msg
                else:
                    # Answer from ACR10
                    if msgLen == 81:
                        print("81", end='')
                        power = True
                    elif msgLen == 89:
                        recvMsg = recvMsg[8:]
                        print("89", end='')
                        power = True
                    elif msgLen == 43:
                        print("43", end='')
                        power = False
                    elif msgLen == 51:
                        print("51", end='')
                        recvMsg = recvMsg[8:]
                        power = False
                    else:
                        print("%2d: " % msgLen, end='')
                        for x in recvMsg:
                            print("%02X " % x, end='')
                        modbus.checkRecvMsgCRC(recvMsg, True)
                        print("Unknown msg")
                        continue
                    if not modbus.checkRecvMsgCRC(recvMsg, True):
                        continue
                    # for x in recvMsg:
                    #     print("%02X " % x, end='')
                    # print(" msg length: %d" % len(recvMsg))
                time.sleep(0.03)
                sendModbusMsg(masterMsg, 0x55)

finally:
    restoreAnykey()

print("Clean exit!")
