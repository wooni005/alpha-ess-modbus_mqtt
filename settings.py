import logging

MQTT_ServerIP      = "192.168.5.248"
MQTT_ServerPort    = 1883

serialPortDevice   = '/dev/ttyUSB0'
serialPortBaudrate = 9600

LOG_FILENAME       = "/home/pi/log/alpha-ess-modbus_mqtt.log"
LOG_LEVEL          = logging.INFO  # Could be e.g. "INFO", "DEBUG" or "WARNING"

MQTT_TOPIC_CONTROL = 'huis/AlphaEss/+/control'

MQTT_TOPIC_CHECK   = "huis/AlphaEss/RPiInfra/check"
MQTT_TOPIC_REPORT  = "huis/AlphaEss/RPiInfra/report"

SEND_INVERTER_MSG_TIMER      = 25   #2.5sec  [100ms]
SEND_METER_MSG_TIMER         = 300  #30sec   [100ms]
SEND_BATTERY_MSG_TIMER       = 300  #30sec   [100ms]
SEND_INVERTER_TEMP_MSG_TIMER = 3000 #5min    [100ms]
