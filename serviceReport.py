import paho.mqtt.publish as mqtt_publish
import json
import time

# external files/classes
import settings

#System check
ACTION_NOTHING   = 0
ACTION_RESTART   = 1
current_sec_time = lambda: int(round(time.time()))

checkMsg = 'OK'
checkFail = False
checkAction = ACTION_NOTHING
checkReport = {}
systemWatchTimer = current_sec_time()


#Called by mqtt
def on_message_check(client, userdata, msgJson):
    if (current_sec_time() - systemWatchTimer) > 300:
        sendCheckReportToHomeLogic(True, ACTION_RESTART, "Timeout systemWatchTimer, 5 min no activity in serialPortThread-thread loop")
    else:
        #print("on_message_check: " + msgJson.topic + ": " + str(msgJson.payload))
        sendCheckReportToHomeLogic(checkFail, checkAction, checkMsg)


#Send the report to the Home Logic system checker
def sendCheckReportToHomeLogic(fail, action, msg):
    global checkMsg
    global checkFail

    checkMsg = msg
    checkFail = fail
    checkReport['checkFail']   = checkFail
    checkReport['checkAction'] = checkAction
    checkReport['checkMsg']    = checkMsg
    mqtt_publish.single(settings.MQTT_TOPIC_REPORT, json.dumps(checkReport), qos=1, hostname=settings.MQTT_ServerIP)


#Don't wait for the Home Logic system checker, report it directly
def sendFailureToHomeLogic(checkAction, checkMsg):
    sendCheckReportToHomeLogic(True, checkAction, checkMsg)
