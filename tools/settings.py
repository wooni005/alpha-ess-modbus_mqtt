import logging

MQTT_ServerIP     = "192.168.5.248"
MQTT_ServerPort   = 1883
serialPortDevice  = '/dev/ttyUSB0'
serialPortBaudrate = 9600
tcpipServerAddress = ('192.168.5.225', 4004)
tcpipServerAddressReader = ('192.168.5.225', 4003)
LOG_FILENAME      = "/home/pi/log/t10_mqtt.log"
LOG_LEVEL = logging.INFO  # Could be e.g. "INFO", "DEBUG" or "WARNING"
# MQTT_TOPIC_OUT       = 'huis/ACR10R/+/out'
MQTT_TOPIC_CHECK     = "huis/ACR10R/RPiHome/check"
MQTT_TOPIC_REPORT    = "huis/ACR10R/RPiHome/report"
