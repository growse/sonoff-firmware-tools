#!/usr/bin/env python3
import argparse
import json
import logging
import re
import time

import paho.mqtt.client as mqtt

parser = argparse.ArgumentParser(description='Upgrade firmware on sonoff-tasmota devices')

parser.add_argument("--hostname", required=True, help="MQTT broker hostname")
parser.add_argument("--port", required=False, help="MQTT broker port", default=1883)
parser.add_argument("--username", required=False, help="MQTT broker username")
parser.add_argument("--password", required=False, help="MQTT broker password")

logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)


def send_version_req_msg(client):
    topic = 'cmnd/sonoffs/status'
    msg = '2'
    logging.debug("publishing {} to {}".format(msg, topic))
    client.publish(topic, msg)


def on_connect(client, userdata, flags, rc):
    msg = None
    if rc == 1:
        msg = "Incorrect protocol version"
    elif rc == 2:
        msg = "Invalid client identifier"
    elif rc == 3:
        msg = "Server unavailable"
    elif rc == 4:
        msg = "Unauthenticated"
    elif rc == 5:
        msg = "Unauthorised"
    elif rc != 0:
        msg = "Invalid client identifier"
    if msg:
        logging.error("Connection refused: {}".format(msg))
        client.disconnect()
        return
    client.subscribe("stat/#", 0)
    send_version_req_msg(client)


status_pattern = re.compile("stat\/([^/]+)\/STATUS2")
discovery_devices = {}


def on_status_message(client, userdata, msg):
    logging.debug("{} {}".format(msg.topic, str(msg.payload)))

    pattern_search = status_pattern.search(msg.topic)
    if pattern_search:
        payload_json = json.loads(msg.payload.decode('utf-8'))
        discovery_devices[pattern_search.group(1)] = payload_json['StatusFWR']['Version']


def discover_devices_and_firmware(client, DISCOVERY_WAIT=1):
    client.on_connect = on_connect
    client.on_message = on_status_message

    client.loop_start()
    time.sleep(DISCOVERY_WAIT)
    client.loop_stop()
    print("Discovered the following devices:")
    for key in discovery_devices.keys():
        print("{}: FW Version: {}".format(key, discovery_devices[key]))
    client.disconnect()


def main(hostname, port, username, password):
    client = mqtt.Client()
    client.username_pw_set(username=username, password=password)
    client.enable_logger()
    client.connect(hostname, port, 60)
    discover_devices_and_firmware(client)


if __name__ == "__main__":
    args = parser.parse_args()
    main(args.hostname, args.port, args.username, args.password)
