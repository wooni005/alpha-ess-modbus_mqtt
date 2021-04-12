#!/usr/bin/python3

import os
import sys
import signal
import serial
import select
import tty
import termios
import time
import traceback
import fcntl
import errno
import struct
import _thread
from queue import Queue

# external files/classes
import modbus
import settings

current_sec_time = lambda: int(round(time.time()))
current_milli_time = lambda: int(round(time.time() * 1000))
usleep = lambda x: time.sleep(x / 1000000.0)
msleep = lambda x: time.sleep(x / 1000.0)

sendQueueBoard = Queue(maxsize=0)

exit = False
serialPort = None
oldSettings = None


def signal_handler(_signal, frame):
    global exit

    print('You pressed Ctrl+C!')
    exit = True


def initAnykey():
    global oldSettings

    oldSettings = termios.tcgetattr(sys.stdin)
    newSettings = termios.tcgetattr(sys.stdin)
    # newSettings[3] = newSettings[3] & ~(termios.ECHO | termios.ICANON) # lflags
    newSettings[3] = newSettings[3] & ~(termios.ECHO | termios.ICANON) # lflags
    newSettings[6][termios.VMIN] = 0  # cc
    newSettings[6][termios.VTIME] = 0 # cc
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
    print('1-Send meter data request to Storion')
    print('2-Send battery data request to Storion')
    print('3-Send inverter data request to Storion')
    print('4-Send inverter data request to Storion')
    print('9-Scan for valid modBus address')
    print('h-Print this help')
    print()


def printHexString(str):
    for char in str:
        print("%02X " % (ord(char)), end='')
    print()


def printHexByteString(recvMsg):
    for x in recvMsg:
        print("%02X " % x, end='')
    print()
    # print(" msg length: %d" % len(recvMsg))


def openSerialPort(serialPortDeviceName):
    try:
        ser = serial.Serial(port=serialPortDeviceName,
                            baudrate=settings.serialPortBaudrate,
                            parity=serial.PARITY_NONE,
                            stopbits=serial.STOPBITS_ONE,
                            bytesize=serial.EIGHTBITS,
                            timeout=0.25)  # 1=1sec 0=non-blocking None=Blocked, 100 bytes by 9600bd=0.01sec

        if ser.isOpen():
            print(("Successfully connected to serial port %s" % (serialPortDeviceName)))

        return ser

    # Handle other exceptions and print the error
    except Exception as arg:
        print("%s" % str(arg))
        traceback.print_exc()
        return None


def closeSerialPort(ser):
    ser.close()


def sendModbusMsg(sendMsg, modBusAddr):
    sendMsgList = list(sendMsg)
    sendMsgList[0] = chr(modBusAddr)
    # print(sendMsgList)
    print("modBusAddr=%d" % modBusAddr, end='')
    print(" -> send request to Storion T10: ", end='')
    sendMsg = ''
    for element in sendMsgList:
        # print("%02X " % ord(element), end='')
        sendMsg += element
    # printHexString(sendMsg)
    request = sendMsg + modbus.calculateCRC(sendMsg)
    printHexString(request)
    sendQueueBoard.put(request.encode('latin1'))
    # sock.send(request.encode('ascii'))


def serialPortThread(serialPortDeviceName, serialPort):
    global checkMsg
    global somethingWrong

    oldTimeout = current_sec_time()

    # Wait a while, the OS is probably testing what kind of device is there
    # with sending 'ATEE' commands and others
    time.sleep(2)
    serialPort.reset_input_buffer()

    # Ask for board Id
    print("serialPortThread started")
    serialPort.setRTS(0) # Disable RS485 send

    while True:
        try:
            if serialPort.isOpen():
                recvMsg = serialPort.read(110)
                # "".join([chr(i) for i in recvMsgWithoutCRC])
            else:
                recvMsg = ""
                time.sleep(5)
                print("Serial Port not open")

            # Check if something is received
            if recvMsg != b"":
                msgLen = len(recvMsg)
                print("Received msgLen: %d msg: " % msgLen) #, end='')

                # Check the receive msg CRC
                if not modbus.checkRecvMsgCRC(recvMsg):
                    printHexByteString(recvMsg)
                    continue

                # Check msgLen (+5 bytes=modBusAddr,Cmnd,dataLength,CRChigh,CRClow)
                if msgLen != (recvMsg[2] + 5):
                    print("Wrong msgLen!", end='')
                    printHexByteString(recvMsg)
                    continue

                # printHexByteString(recvMsg)
                # Received meter data
                if msgLen == 49:
                    printHexByteString(recvMsg)
                    sensorData = {}
                    # 0-2: Header

                    i = 3
                    val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    print("Active power of A phase(Grid Meter): %3dW  " % val) #, end='')
                    sensorData['Pphase_a'] = val

                    i = 7
                    val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    print("Active power of B phase(Grid Meter): %3dW  " % val) #, end='')
                    sensorData['Pphase_b'] = val

                    i = 11
                    val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    print("Active power of C phase(Grid Meter): %3dW  " % val) #, end='')
                    sensorData['Pphase_c'] = val

                    i = 15
                    val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    print("Total active power (Grid meter): %3dW  " % val) #, end='')
                    sensorData['Pactive'] = val

                    i = 19
                    val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    print("Feed to grid (Grid meter): %.2fkWh" % (float(val) / 100)) #, end=''), end='')
                    sensorData['Pgrid'] = val

                    i = 23
                    val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    print("Consume to grid (Grid meter): %.2fkWh" % (float(val) / 100)) #, end=''), end='')
                    sensorData['Pcons'] = val

                    # i=27: Not used (Active power of A phase(PV Meter))
                    # i=31: Not used (Active power of B phase(PV Meter))
                    # i=35: Not used (Active power of C phase(PV Meter))

                    i = 39
                    val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    print("Total active power (PV meter): %3dW  " % val) #, end=''), end='')
                    sensorData['Pactive'] = val

                    i = 43
                    val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    print("Feed to grid (PV meter): %.2fkWh" % (float(val) / 100)) #, end=''), end='')
                    sensorData['Pgrid'] = val

                # Received battery data
                elif msgLen == 81:
                    printHexByteString(recvMsg)
                    i = 3
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    print("Battery voltage: %.1f V" % (float(val) / 10))

                    i = 5
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    print("Battery current: %.1f A" % (float(val) / 10))

                    i = 7
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    print("Battery SOC: %.1f %%" % (float(val) / 10))

                    i = 9
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    print("Battery status: %d" % val)

                    i = 11
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    print("Battery relay status: %d" % val)

                    i = 13
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    print("Pack ID of min cell voltage: %d" % val)

                    i = 15
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    print("Cell ID of min cell voltage: %d" % val)

                    i = 17
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    print("Min cell voltage: %.3f V" % (float(val) / 1000))

                    i = 19
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    print("Pack ID of max cell voltage: %d" % val)

                    i = 21
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    print("Cell ID of max cell voltage: %d" % val)

                    i = 23
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    print("Max cell voltage: %.3f V" % (float(val) / 1000))

                    i = 25 #0x10B
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    print("Pack ID of min cell temp: %d" % val)

                    i = 27 #0x10C
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    print("Cell ID of min cell temp: %d" % val)

                    i = 29 #0x10D
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    print("Min cell temp: %.1f ℃" % (float(val) / 10))

                    i = 31 #0x10E
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    print("Pack ID of max cell temp: %d" % val)

                    i = 33 #0x10F
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    print("Cell ID of max cell temp: %d" % val)

                    i = 35 #0x110
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    print("Max cell temp: %.1f ℃" % (float(val) / 10))

                    i = 37 #0x111
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    print("Max charge current: %.1f A" % (float(val) / 10))

                    i = 39 #0x112
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    print("Max discharge current: %.1f A" % (float(val) / 10))

                    i = 41 #0x113
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    print("Charge cut-off voltage: %.1f V" % (float(val) / 10))

                    i = 43 #0x114
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    print("Discharge cut-off voltage: %.1f V" % (float(val) / 10))

                    i = 45 #0x115
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    print("BMU software version: %d" % val)

                    i = 47 #0x116
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    print("LMU software version: %d" % val)

                    i = 49 #0x117
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    print("ISO software version: %d" % val)

                    i = 51 #0x118
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    print("Battery num: %d" % val)

                    i = 53 #0x119
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    print("Battery capacity: %.1f kWh" % (float(val) / 10))

                    i = 55 #0x11A
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    print("Battery type: %d" % val)

                    i = 57 #0x11B
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    print("Battery SOH: %.1f %%" % (float(val) / 10))

                    i = 59 #0x11C
                    val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    print("Battery warning: %d" % val)

                    i = 63 #0x11E
                    val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    print("Battery fault: %d" % val)

                    i = 67 #0x120
                    val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    print("Charge energy: %.1f kWh" % (float(val) / 10))

                    i = 71 #0x122
                    val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    print("Discharge energy: %.1f kWh" % (float(val) / 10))

                    i = 75 #0x124
                    val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    print("Charge energy from grid: %.1f kWh" % (float(val) / 10))

                # Received inverter data
                elif msgLen == 101:
                    printHexByteString(recvMsg)

                    i = 3
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    print("Inverter voltage L1: %.1f V" % (float(val) / 10))

                    i = 5
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    print("Inverter voltage L2: %.1f V" % (float(val) / 10))

                    i = 7
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    print("Inverter voltage L3: %.1f V" % (float(val) / 10))

                    i = 9
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    print("Inverter current L1: %.1f A" % (float(val) / 10))

                    i = 11
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    print("Inverter current L2: %.1f A" % (float(val) / 10))

                    i = 13
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    print("Inverter current L3: %.1f A" % (float(val) / 10))

                    i = 15
                    val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    print("Inverter power L1: %d W" % val)

                    i = 19
                    val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    print("Inverter power L2: %d W" % val)

                    i = 23
                    val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    print("Inverter power L3: %d W" % val)

                    i = 27 #0x40C
                    val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    print("Inverter power total: %d W" % val)

                    i = 31
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    print("Inverter backup voltage L1: %.1f V" % (float(val) / 10))

                    i = 33
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    print("Inverter backup voltage L2: %.1f V" % (float(val) / 10))

                    i = 35
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    print("Inverter backup voltage L3: %.1f V" % (float(val) / 10))

                    i = 37
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    print("Inverter backup current L1: %.1f A" % (float(val) / 10))

                    i = 39
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    print("Inverter backup current L2: %.1f A" % (float(val) / 10))

                    i = 41
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    print("Inverter backup current L3: %.1f A" % (float(val) / 10))

                    i = 43
                    val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    print("Inverter backup power L1: %d W" % val)

                    i = 47
                    val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    print("Inverter backup power L2: %d W" % val)

                    i = 51
                    val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    print("Inverter backup power L3: %d W" % val)

                    i = 55
                    val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    print("Inverter backup power total: %d W" % val)

                    i = 59
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    print("Inverter grid frequency: %.2f Hz" % (float(val) / 100))

                    i = 61
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    print("PV1 Voltage: %.1f V" % (float(val) / 10))

                    i = 63
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    print("PV1 Current: %.1f A" % (float(val) / 10))

                    i = 65 # 0x41F
                    val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    print("PV1 power: %d W" % val)

                    i = 69
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    print("PV2 Voltage: %.1f V" % (float(val) / 10))

                    i = 71
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    print("PV2 Current: %.1f A" % (float(val) / 10))

                    i = 73
                    val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    print("PV2 power: %d W" % val)

                    i = 77
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    print("PV3 Voltage: %.1f V" % (float(val) / 10))

                    i = 79
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    print("PV3 Current: %.1f A" % (float(val) / 10))

                    i = 81
                    val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    print("PV3 power: %d W" % val)

                    i = 85
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    print("Inverter temp: %.1f ℃" % (float(val) / 10))

                    i = 89
                    val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    print("Inverter warning: %d" % val)

                    i = 93
                    val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    print("Inverter fault: %d" % val)

                    i = 97
                    val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    print("Total PV Energy: %.1f kWh" % (float(val) / 10))

                # Received system data
                elif msgLen == 17:
                    printHexByteString(recvMsg)

                    i = 3
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    print("Feed into grid: %d %%" % val)

                    i = 5
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    print("System fault: %d" % val)

                    i = 7
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    print("Year-month: %04x" % val)

                    i = 9
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    print("Day-hour: %04x" % val)

                    i = 11
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    print("Minute-second: %04x" % val)

                else:
                    print("Unknown data msg received")
                    printHexByteString(recvMsg)

                # Check the Rx timeout
                if (current_sec_time() - oldTimeout) > 300:
                    # Reset the rx timeout timer
                    oldTimeout = current_sec_time()

            # Check if there is any message to send
            if not sendQueueBoard.empty():
                serialPort.setRTS(1) # Enable RS485 send
                sendMsg = sendQueueBoard.get_nowait()
                msgLen = len(sendMsg)
                # print(("SendMsg: %s" % sendMsg))
                # printHexByteString(sendMsg)
                serialPort.write(sendMsg)
                # 9600 baud->1bit=104,1667uS
                # 1 byte=10bits->10*104,1667=1041,667uS
                usleep(msgLen * 1041.6667)
                # msleep(8)

                # if sendMsg != "":
                #     serialPort.write(sendMsg)
                serialPort.setRTS(0) # Disable RS485 send
                # print("Tx ready")

            time.sleep(0.05)

        # In case the message contains unusual data
        except ValueError as arg:
            print(arg)
            traceback.print_exc()
            time.sleep(1)

        # Quit the program by Ctrl-C
        except KeyboardInterrupt:
            print("Program aborted by Ctrl-C")
            exit()

        # Handle other exceptions and print the error
        except Exception as arg:
            print("Exception in serialPortThread serialPortDeviceName:%s" % serialPortDeviceName)
            print("%s" % str(arg))
            traceback.print_exc()
            time.sleep(120)


###
# Initalisation ####
###

# Init signal handler, because otherwise Ctrl-C does not work
signal.signal(signal.SIGINT, signal_handler)

# Make the following devices accessable for user
# os.system("sudo chmod 666 %s" % settings.serialPortDevice)

# Give Home Assistant and Mosquitto the time to startup
time.sleep(2)

# BatteryLevel: 0x102
testMsg     = "\x55\x03\x00\x00\x00\x0D" #, 0x89, 0xDB]
meterMsg    = "\x55\x03\x00\x00\x00\x16"
batteryMsg  = "\x55\x03\x01\x00\x00\x26"
inverterMsg = "\x55\x03\x04\x00\x00\x30"
systemMsg   = "\x55\x03\x07\x00\x00\x06"

sendCrLf = False

serialPort = openSerialPort(settings.serialPortDevice)

if serialPort is None:
    print("Program terminated.")
    sys.exit(1)
else:
    _thread.start_new_thread(serialPortThread, (settings.serialPortDevice, serialPort))

    powerCntAdd = 0
    powerAvgAdd = 0

    modBusAddr = 0x00
    sendDelayTimer = 0
    autoSend = False

    printHelp()
    initAnykey()

try:
    while not exit:
        if sendDelayTimer >= 5:
            sendDelayTimer = 0
            modBusAddr = modBusAddr + 1
            if modBusAddr >= 248:
                # modBusAddr = 1
                autoSend = False
            sendModbusMsg(testMsg, modBusAddr)
            if not autoSend:
                print("Autosend stopped")

        ch = os.read(sys.stdin.fileno(), 1)
        if ch != b'':
            # Key is pressed
            if ch == b'\x1b':
                print("Escape pressed: Exit")
                exit = True
            elif ch == b'r':
                print("Reset powerAvg")
                powerCntAdd = 0
                powerAvgAdd = 0

            # Get Meter data
            elif ch == b'1':
                sendDelayTimer = 0
                sendModbusMsg(meterMsg, 0x55)

            # Get battery data
            elif ch == b'2':
                sendDelayTimer = 0
                sendModbusMsg(batteryMsg, 0x55)

            # Get inverter data
            elif ch == b'3':
                sendDelayTimer = 0
                sendModbusMsg(inverterMsg, 0x55)

            # Get system data
            elif ch == b'4':
                sendDelayTimer = 0
                sendModbusMsg(systemMsg, 0x55)

            if ch == b'9':
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
        time.sleep(0.1)
        if autoSend:
            sendDelayTimer = sendDelayTimer + 1


finally:
    serialPort.setRTS(0) # Disable RS485 send
    restoreAnykey()
    closeSerialPort(serialPort)

print("Clean exit!")
