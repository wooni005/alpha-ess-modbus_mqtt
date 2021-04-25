#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os
import sys
import signal
import time
import serial
import struct
import _thread
import traceback
from queue import Queue
import json
import paho.mqtt.publish as mqtt_publish
import paho.mqtt.client as mqtt_client

# external files/classes
import modbus
import settings
import logger
import serviceReport

sendQueue = Queue(maxsize=0)
current_sec_time = lambda: int(round(time.time()))
usleep = lambda x: time.sleep(x / 1000000.0)

testMsg     = "\x55\x03\x00\x00\x00\x0D" #, 0x89, 0xDB]
meterMsg    = "\x55\x03\x00\x00\x00\x16"
batteryMsg  = "\x55\x03\x01\x00\x00\x26"
inverterMsg = "\x55\x03\x04\x00\x00\x30"
systemMsg   = "\x55\x03\x07\x00\x00\x06"

exit = False
serialPort = None
inverterTemp = None


def signal_handler(_signal, frame):
    global exit

    print('You pressed Ctrl+C!')
    exit = True


def printHexString(str):
    for char in str:
        print("%02X " % (ord(char)), end='')
    print()


def printHexByteString(recvMsg):
    for x in recvMsg:
        print("%02X " % x, end='')
    print()
    # print(" msg length: %d" % len(recvMsg))


# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("MQTT Client connected successfully")
        client.subscribe([(settings.MQTT_TOPIC_CONTROL, 1), (settings.MQTT_TOPIC_CHECK, 1)])
    else:
        print(("ERROR: MQTT Client connected with result code %s " % str(rc)))


# The callback for when a PUBLISH message is received from the server
def on_message(client, userdata, msg):
    print(('ERROR: Received ' + msg.topic + ' in on_message function' + str(msg.payload)))


def on_message_homelogic(client, userdata, msg):
    #print(msg.topic + " " + str(msg.payload))
    topics = msg.topic.split("/")

    deviceName = topics[2] #huis/RFXtrx/KaKu-12/out
    cmnd = deviceName.split("-") #KaKu-12

    # KaKu-12
    if cmnd[0] == "KaKu":
        #print("Activate KaKu WCD: %s" % cmnd[1])
        # setKaKu(int(cmnd[1]), msg.payload)
        pass


def openSerialPort():
    global exit
    try:
        ser = serial.Serial(port=settings.serialPortDevice,  # port='/dev/ttyACM0',
                            baudrate=settings.serialPortBaudrate,
                            parity=serial.PARITY_NONE,
                            stopbits=serial.STOPBITS_ONE,
                            bytesize=serial.EIGHTBITS,
                            timeout=1)  # 1=1sec 0=non-blocking None=Blocked

        if ser.isOpen():
            print(("rflink_mqtt: Successfully connected to serial port %s" % (settings.serialPortDevice)))

        return ser

    # Handle other exceptions and print the error
    except Exception as arg:
        print("%s" % str(arg))
        # traceback.print_exc()

        #Report failure to Home Logic system check
        serviceReport.sendFailureToHomeLogic(serviceReport.ACTION_NOTHING, 'Serial port open failure on port %s, wrong port or USB cable missing' % (settings.serialPortDevice))

        # Suppress restart loops
        time.sleep(900) # 15 min
        exit = True


def closeSerialPort(ser):
    ser.close()


def serialPortThread(serialPortDeviceName, serialPort):
    global exit
    global checkMsg
    global somethingWrong
    global inverterTemp

    # Wait a while, the OS is probably testing what kind of device is there
    # with sending 'ATEE' commands and others
    time.sleep(2)
    serialPort.reset_input_buffer()

    # Ask for board Id
    print("serialPortThread started")
    serialPort.setRTS(0) # Disable RS485 send

    while not exit:
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
                # print("Received msgLen: %d msg: " % msgLen) #, end='')

                # Check the receive msg CRC
                if not modbus.checkRecvMsgCRC(recvMsg):
                    printHexByteString(recvMsg)
                    continue

                # Check msgLen (+5 bytes=modBusAddr,Cmnd,dataLength,CRChigh,CRClow)
                if msgLen != (recvMsg[2] + 5):
                    print("Wrong msgLen!", end='')
                    printHexByteString(recvMsg)
                    continue

                # Reset the Rx timeout timer
                serviceReport.systemWatchTimer = current_sec_time()

                # printHexByteString(recvMsg)
                # Received meter data
                if msgLen == 49:
                    # printHexByteString(recvMsg)
                    sensorData = {}
                    # 0-2: Header

                    i = 3
                    val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    # print("Active power of A phase(Grid Meter): %3dW  " % val) #, end='')
                    # sensorData['Pphase_a'] = val

                    i = 7
                    val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    # print("Active power of B phase(Grid Meter): %3dW  " % val) #, end='')
                    # sensorData['Pphase_b'] = val

                    i = 11
                    val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    # print("Active power of C phase(Grid Meter): %3dW  " % val) #, end='')
                    # sensorData['Pphase_c'] = val

                    i = 15
                    val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    # print("Total active power (Grid meter): %3dW  " % val) #, end='')
                    sensorData['Pactive'] = val

                    i = 19
                    val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    # print("Feed to grid (Grid meter): %.2fkWh" % (float(val) / 100)) #, end=''), end='')
                    sensorData['Egrid'] = float(val) / 100

                    i = 23
                    val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    # print("Consume to grid (Grid meter): %.2fkWh" % (float(val) / 100)) #, end=''), end='')
                    sensorData['Econs'] = float(val) / 100

                    # i=27: Not used (Active power of A phase(PV Meter))
                    # i=31: Not used (Active power of B phase(PV Meter))
                    # i=35: Not used (Active power of C phase(PV Meter))

                    # i = 39
                    # val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    # print("Total active power (PV meter): %3dW  " % val) #, end=''), end='')
                    # sensorData['Pactive'] = val

                    # i = 43
                    # val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    # print("Feed to grid (PV meter): %.2fkWh" % (float(val) / 100)) #, end=''), end='')
                    # sensorData['Pgrid'] = val

                    mqtt_publish.single("huis/AlphaEss/Meter/power", json.dumps(sensorData, separators=(', ', ':')), hostname=settings.MQTT_ServerIP, retain=True)

                # Received battery data
                elif msgLen == 81:
                    # printHexByteString(recvMsg)
                    sensorData = {}

                    i = 3
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    sensorData['Ubatt'] = float(val) / 10
                    # print("Battery voltage: %.1f V" % (float(val) / 10))

                    i = 5
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    sensorData['Ibatt'] = float(val) / 10
                    # print("Battery current: %.1f A" % (float(val) / 10))

                    i = 7
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    sensorData['SOC'] = float(val) / 10
                    # print("Battery SOC: %.1f %%" % (float(val) / 10))

                    i = 9
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    sensorData['Status'] = val
                    # print("Battery status: %d" % val)

                    i = 11
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    sensorData['Relay_status'] = val
                    # print("Battery relay status: %d" % val)

                    # i = 13
                    # val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    # sensorData['PackID_Umin'] = val
                    # # print("Pack ID of min cell voltage: %d" % val)

                    # i = 15
                    # val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    # sensorData['CellID_Umin'] = val
                    # # print("Cell ID of min cell voltage: %d" % val)

                    i = 17
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    sensorData['Umin'] = float(val) / 1000
                    # print("Min cell voltage: %.3f V" % (float(val) / 1000))

                    # i = 19
                    # val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    # sensorData['PackID_Umax'] = val
                    # # print("Pack ID of max cell voltage: %d" % val)

                    # i = 21
                    # val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    # sensorData['CellID_Umax'] = val
                    # # print("Cell ID of max cell voltage: %d" % val)

                    i = 23
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    sensorData['Umax'] = float(val) / 1000
                    # print("Max cell voltage: %.3f V" % (float(val) / 1000))

                    i = 29 #0x10D
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    sensorData['Tmin'] = float(val) / 10
                    # print("Min cell temp: %.1f ℃" % (float(val) / 10))

                    i = 35 #0x110
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    sensorData['Tmax'] = float(val) / 10
                    # print("Max cell temp: %.1f ℃" % (float(val) / 10))

                    i = 37 #0x111
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    sensorData['Icharge_max'] = float(val) / 10
                    # print("Max charge current: %.1f A" % (float(val) / 10))

                    i = 39 #0x112
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    sensorData['Idischarge_max'] = float(val) / 10
                    # print("Max discharge current: %.1f A" % (float(val) / 10))

                    i = 41 #0x113
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    sensorData['Ucharge_cut_off'] = float(val) / 10
                    # print("Charge cut-off voltage: %.1f V" % (float(val) / 10))

                    i = 43 #0x114
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    sensorData['Udischarge_cut_off'] = float(val) / 10
                    # print("Discharge cut-off voltage: %.1f V" % (float(val) / 10))

                    # i = 45 #0x115
                    # val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    # print("BMU software version: %d" % val)

                    # i = 47 #0x116
                    # val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    # print("LMU software version: %d" % val)

                    # i = 49 #0x117
                    # val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    # print("ISO software version: %d" % val)

                    # i = 51 #0x118
                    # val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    # print("Battery num: %d" % val)

                    # i = 53 #0x119
                    # val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    # print("Battery capacity: %.1f kWh" % (float(val) / 10))

                    # i = 55 #0x11A
                    # val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    # print("Battery type: %d" % val)

                    i = 57 #0x11B
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    sensorData['SOH'] = float(val) / 10
                    # print("Battery SOH: %.1f %%" % (float(val) / 10))

                    i = 59 #0x11C
                    val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    sensorData['Warning'] = val
                    # print("Battery warning: %d" % val)

                    i = 63 #0x11E
                    val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    sensorData['Fault'] = val
                    # print("Battery fault: %d" % val)

                    i = 67 #0x120
                    val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    sensorData['Echarge'] = float(val) / 10
                    # print("Charge energy: %.1f kWh" % (float(val) / 10))

                    i = 71 #0x122
                    val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    sensorData['Edischarge'] = float(val) / 10
                    # print("Discharge energy: %.1f kWh" % (float(val) / 10))

                    i = 75 #0x124
                    val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    sensorData['Echarge_from_grid'] = float(val) / 10
                    # print("Charge energy from grid: %.1f kWh" % (float(val) / 10))

                    mqtt_publish.single("huis/AlphaEss/Battery/power", json.dumps(sensorData, separators=(', ', ':')), hostname=settings.MQTT_ServerIP, retain=True)

                # Received inverter data
                elif msgLen == 101:
                    # printHexByteString(recvMsg)
                    sensorData = {}
                    i = 3
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    sensorData['Uinv_L1'] = float(val) / 10
                    # print("Inverter voltage L1: %.1f V" % (float(val) / 10))

                    i = 5
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    sensorData['Uinv_L2'] = float(val) / 10
                    # print("Inverter voltage L2: %.1f V" % (float(val) / 10))

                    i = 7
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    sensorData['Uinv_L3'] = float(val) / 10
                    # print("Inverter voltage L3: %.1f V" % (float(val) / 10))

                    # i = 9
                    # val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    # print("Inverter current L1: %.1f A" % (float(val) / 10))

                    # i = 11
                    # val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    # print("Inverter current L2: %.1f A" % (float(val) / 10))

                    # i = 13
                    # val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    # print("Inverter current L3: %.1f A" % (float(val) / 10))

                    # i = 15
                    # val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    # print("Inverter power L1: %d W" % val)

                    # i = 19
                    # val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    # print("Inverter power L2: %d W" % val)

                    # i = 23
                    # val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    # print("Inverter power L3: %d W" % val)

                    i = 27 #0x40C
                    val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    sensorData['Pinv'] = val
                    # print("Inverter power total: %d W" % val)

                    i = 31
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    sensorData['Uback_L1'] = float(val) / 10
                    # print("Inverter backup voltage L1: %.1f V" % (float(val) / 10))

                    i = 33
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    sensorData['Uback_L2'] = float(val) / 10
                    # print("Inverter backup voltage L2: %.1f V" % (float(val) / 10))

                    i = 35
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    sensorData['Uback_L3'] = float(val) / 10
                    # print("Inverter backup voltage L3: %.1f V" % (float(val) / 10))

                    # i = 37
                    # val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    # print("Inverter backup current L1: %.1f A" % (float(val) / 10))

                    # i = 39
                    # val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    # print("Inverter backup current L2: %.1f A" % (float(val) / 10))

                    # i = 41
                    # val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    # print("Inverter backup current L3: %.1f A" % (float(val) / 10))

                    # i = 43
                    # val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    # print("Inverter backup power L1: %d W" % val)

                    # i = 47
                    # val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    # print("Inverter backup power L2: %d W" % val)

                    # i = 51
                    # val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    # print("Inverter backup power L3: %d W" % val)

                    i = 55
                    val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    sensorData['Pback'] = val
                    # print("Inverter backup power total: %d W" % val)

                    # i = 59
                    # val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    # print("Inverter grid frequency: %.2f Hz" % (float(val) / 100))

                    i = 61
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    sensorData['U_PV1'] = float(val) / 10
                    # print("PV1 Voltage: %.1f V" % (float(val) / 10))

                    i = 63
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    sensorData['I_PV1'] = float(val) / 10
                    # print("PV1 Current: %.1f A" % (float(val) / 10))

                    i = 65 # 0x41F
                    val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    sensorData['P_PV1'] = val
                    # print("PV1 power: %d W" % val)

                    # i = 69
                    # val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    # print("PV2 Voltage: %.1f V" % (float(val) / 10))

                    # i = 71
                    # val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    # print("PV2 Current: %.1f A" % (float(val) / 10))

                    # i = 73
                    # val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    # print("PV2 power: %d W" % val)

                    # i = 77
                    # val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    # print("PV3 Voltage: %.1f V" % (float(val) / 10))

                    # i = 79
                    # val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    # print("PV3 Current: %.1f A" % (float(val) / 10))

                    # i = 81
                    # val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    # print("PV3 power: %d W" % val)

                    i = 85
                    val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                    inverterTemp = float(val) / 10
                    sensorData['TempInv'] = inverterTemp

                    i = 89
                    val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    sensorData['Warning'] = val
                    # print("Inverter warning: %d" % val)

                    i = 93
                    val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    sensorData['Fault'] = val
                    # print("Inverter fault: %d" % val)

                    # i = 97
                    # val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    # sensorData['Epv'] = float(val) / 10
                    # print("Total PV Energy: %.1f kWh" % (float(val) / 10))

                    mqtt_publish.single("huis/AlphaEss/Inverter/power", json.dumps(sensorData, separators=(', ', ':')), hostname=settings.MQTT_ServerIP, retain=True)

                # # Received system data
                # elif msgLen == 17:
                #     # printHexByteString(recvMsg)
                #     sensorData = {}
                #     i = 3
                #     val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                #     print("Feed into grid: %d %%" % val)

                #     i = 5
                #     val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                #     print("System fault: %d" % val)

                #     i = 7
                #     val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                #     print("Year-month: %04x" % val)

                #     i = 9
                #     val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                #     print("Day-hour: %04x" % val)

                #     i = 11
                #     val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                #     print("Minute-second: %04x" % val)

                else:
                    print("Unknown data msg received")
                    printHexByteString(recvMsg)

            # Check if there is any message to send
            if not sendQueue.empty():
                serialPort.setRTS(1) # Enable RS485 send
                sendMsg = sendQueue.get_nowait()
                msgLen = len(sendMsg)
                # print(("SendMsg: %s" % sendMsg))
                # printHexByteString(sendMsg)
                serialPort.write(sendMsg)
                # 9600 baud->1bit=104,1667uS
                # 1 byte=10bits->10*104,1667=1041,667uS
                usleep(msgLen * 1041.6667)
                # msleep(8)

                serialPort.setRTS(0) # Disable RS485 send
                # print("Tx ready")

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


def sendModbusMsg(sendMsg, modBusAddr):
    sendMsgList = list(sendMsg)
    sendMsgList[0] = chr(modBusAddr)
    # print(sendMsgList)
    # print("modBusAddr=%d" % modBusAddr, end='')
    # print(" -> send request to Storion T10: ", end='')
    sendMsg = ''
    for element in sendMsgList:
        # print("%02X " % ord(element), end='')
        sendMsg += element
    # printHexString(sendMsg)
    request = sendMsg + modbus.calculateCRC(sendMsg)
    # printHexString(request)
    sendQueue.put(request.encode('latin'))


def print_time(delay):
    count = 0
    while count < 5:
        time.sleep(delay)
        count += 1
        print("%s" % (time.ctime(time.time())))


###
# Initalisation ####
###
logger.initLogger(settings.LOG_FILENAME)

# Init signal handler, because otherwise Ctrl-C does not work
signal.signal(signal.SIGINT, signal_handler)

# Make the following devices accessable for user
os.system("sudo chmod 666 %s" % settings.serialPortDevice)

# Give Home Assistant and Mosquitto the time to startup
time.sleep(2)

serialPort = openSerialPort()

if serialPort is None:
    print("Program terminated.")
    sys.exit(1)
else:
    # Create the serialPortThread
    try:
        # thread.start_new_thread( print_time, (60, ) )
        _thread.start_new_thread(serialPortThread, (settings.serialPortDevice, serialPort))
    except Exception:
        print("Error: unable to start the serialPortThread")
        sys.exit(1)

# Start the MQTT client
client = mqtt_client.Client()
client.message_callback_add(settings.MQTT_TOPIC_CONTROL,   on_message_homelogic)
client.message_callback_add(settings.MQTT_TOPIC_CHECK,     serviceReport.on_message_check)
client.on_connect = on_connect
client.on_message = on_message
client.connect(settings.MQTT_ServerIP, settings.MQTT_ServerPort, 60)
client.loop_start()

# The thread is waiting 2 sec, so also wait here before sending msgs
time.sleep(2)

try:
    sendGetMeterStatusTimer = settings.SEND_METER_MSG_TIMER - 15 #[100ms]
    sendGetBatteryStatusTimer = settings.SEND_BATTERY_MSG_TIMER - 3 #[100ms]
    sendGetInverterStatusTimer = settings.SEND_INVERTER_MSG_TIMER - 28 #[100ms]
    sendInverterTempTimer = settings.SEND_INVERTER_TEMP_MSG_TIMER - 100

    while not exit:
        # Get inverter status every 5 sec
        if sendGetInverterStatusTimer >= settings.SEND_INVERTER_MSG_TIMER:
            sendGetInverterStatusTimer = 0

            # Get inverter data
            sendModbusMsg(inverterMsg, 0x55)

        # Get meter status every 30 sec
        if sendGetMeterStatusTimer >= settings.SEND_METER_MSG_TIMER:
            sendGetMeterStatusTimer = 0

            # Get Meter data
            sendModbusMsg(meterMsg, 0x55)

        # Get battery status every 30 sec
        if sendGetBatteryStatusTimer >= settings.SEND_BATTERY_MSG_TIMER:
            sendGetBatteryStatusTimer = 0

            # Get battery data
            sendModbusMsg(batteryMsg, 0x55)

        if (inverterTemp is not None) and (sendInverterTempTimer >= settings.SEND_INVERTER_TEMP_MSG_TIMER):
            sendInverterTempTimer = 0
            # print("Inverter temp: %.1f ℃" % inverterTemp)
            tempData = {}
            tempData['Temperature'] = "%1.1f" % inverterTemp
            mqtt_publish.single("huis/AlphaEss/Temp-Inverter/temp", json.dumps(tempData, separators=(', ', ':')), hostname=settings.MQTT_ServerIP, retain=True)

        sendGetInverterStatusTimer += 1 #[100ms]
        sendGetMeterStatusTimer += 1 #[100ms]
        sendGetBatteryStatusTimer += 1 #[100ms]
        sendInverterTempTimer += 1 #[100ms]
        time.sleep(0.1) #[100ms]

finally:
    if serialPort is not None:
        serialPort.setRTS(0) # Disable RS485 send
        closeSerialPort(serialPort)
        print('Closed serial port')

print("Clean exit!")
