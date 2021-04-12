import logging

MQTT_ServerIP     = "192.168.5.248"
MQTT_ServerPort   = 1883

serialPortDevice  = '/dev/ttyUSB0'
serialPortBaudrate = 9600

LOG_FILENAME      = "/home/pi/log/alpha-ess-modbus_mqtt.log"
LOG_LEVEL = logging.INFO  # Could be e.g. "INFO", "DEBUG" or "WARNING"
# MQTT_TOPIC_OUT       = 'huis/ACR10R/+/out'
MQTT_TOPIC_CHECK     = "huis/AlphaEss/RPiInfra/check"
MQTT_TOPIC_REPORT    = "huis/AlphaEss/RPiInfra/report"
