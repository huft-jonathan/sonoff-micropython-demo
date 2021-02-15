"""
mosquitto_pub -h zukunft -t "sonoff-f35a4500/state" -m "0"
mosquitto_pub -h zukunft -t "sonoff-f35a4500/state" -m "1"
"""

import gc
import machine
import network
import utime
import ubinascii

from umqtt_robust import MQTTClient


MQTT_SERVER = "--------"
WLAN_SSID = "--------"
WLAN_KEY = "--------"


def connect_station(hostname=None):
    sta_if = network.WLAN(network.STA_IF)
    print('Connecting to network...')
    if hostname:
        sta_if.config(dhcp_hostname=hostname)
    sta_if.active(True)
    sta_if.connect(WLAN_SSID, WLAN_KEY)
    while not sta_if.isconnected():
        pass
    print('Network config:', sta_if.ifconfig())
    return sta_if


def sub_cb(topic, msg):
    global relay
    if msg == b"1":
        relay.value(1)
    elif msg == b"0":
        relay.value(0)


boot_t = utime.time()
print("Starting..")

led = machine.Pin(13, machine.Pin.OUT)
led.value(0)

relay = machine.Pin(12, machine.Pin.OUT)
relay.value(0)

ap_if = network.WLAN(network.AP_IF)
ap_if.active(True)
ap_connected = True

c = MQTTClient("sonoff-%s" % ubinascii.hexlify(machine.unique_id()),
               MQTT_SERVER,
               keepalive=600)
c.set_callback(sub_cb)

sta_if = None

while True:

    if not sta_if or not sta_if.isconnected():
        print("(Re)connecting to network..")
        sta_if = connect_station()

    if sta_if.isconnected():
        print("Connecting MQTT..")
        c.connect(clean_session=True)
        topic = b"sonoff-%s/state" % ubinascii.hexlify(machine.unique_id())
        c.subscribe(topic, qos=0)
        print("Connected to %s, subscribed to %s topic" % (
            MQTT_SERVER, topic))

    ping_t = 0
    try:
        while True:
            utime.sleep(1)
            now = utime.time()

            if sta_if.isconnected():
                c.check_msg()
            else:
                break

            if now - ping_t > 45:
                c.ping()
                ping_t = now
                print("MQTT Ping")

            if ap_connected and now - boot_t > 600:
                # Turn AP off a few minutes after powerup.
                print("Disconnecting AP..")
                ap_if = network.WLAN(network.AP_IF)
                ap_if.active(False)
                ap_connected = False
                gc.collect()

    finally:
        print("Left main loop..")
        if sta_if.isconnected():
            print("Disconnecting MQTT..")
            c.disconnect()
