# Payload docs: https://forum.bierbot.com/biewtopic.php?t=51
# {
#  "apikey": "J1okPxXwdFoSvt9Bnz5V",
#  "type": "tilt",
#  "brand": "tilt_bridge",
#  "version": "0.0.1",
#  "chipid": "ORANGE",
#  "s_number_wort_0": 7.9,
#  "s_number_temp_0": 14.3,
#  "s_number_voltage_0": 4.09,
#  "s_number_wifi_0": -90,
#  "s_number_tilt_0": 40.23,
# }
# URL: https://brewbricks.com/api/iot/v1

import datetime
import logging
import os
import json
from typing import Dict

import sentry_sdk

from TiltHydrometer import TiltHydrometer
import requests

LOG = logging.getLogger("tilt")

class BierbotTarget:
    VERSION = "1.0"

    BIERBOT_SEND_FREQUENCY = datetime.timedelta(seconds=3)

    def __init__(self):
        self.enabled = False
        self.target_url = None
        self.data_last_sent = datetime.datetime.now()

    def load_config(self):
        self.enabled = os.environ.get("BIERBOT_TARGET_ENABLED", "false").lower() == 'true'
        self.target_url = os.environ.get("BIERBOT_TARGET_URL")

        if not self.enabled:
            LOG.info("Logging to Bierbot Target is disabled")
        else:
            if not self.target_url:
                LOG.error("Logging to Bierbot Target is enabled, but target URL is invalid")
            else:
                LOG.info(f"Logging to Bierbot Target is enabled, with target URL {self.target_url}")

    @staticmethod
    def convert_tilts_to_list(tilts: Dict[str, TiltHydrometer]) -> list[dict]:
            """Loop through a list of TiltHydrometer objects and convert them to something serializable"""
            tilt_list = []
            for color, tilt in tilts.items():
                if not tilt.expired():
                    tilt_list.append(tilt.to_dict())
            return tilt_list

    @staticmethod
    def gen_json_payload(target_dict: Dict[str, any]) -> dict:
        tilt_dict = target_dict.get('tilts', [])
        if not tilt_dict:
            print("No tilt data found")
            return {}  # Return an empty dictionary if tilt data is empty

        tilt_data = tilt_dict[0]

        wort = float(tilt_data.get('smoothed_gravity', 0))
        temp = (float(tilt_data.get('smoothed_temp', 0)) - 32) * 5 / 9  # Convert F to C

        payload = {
            'apikey': os.environ.get("BIERBOT_APIKEY"),
            'type': 'tilt',
            'brand': 'tiltbridge_junior',
            'version': BierbotTarget.VERSION,
            'chipid': tilt_data.get('color', ''),
            's_number_wort_0': round(wort, 3),
            's_number_temp_0': round(temp, 2),
            's_number_voltage_0': float(tilt_data.get('weeks_on_battery', 0)),
            's_number_wifi_0': tilt_data.get('rssi', -1),
            's_number_tilt_0': 123.456  # Placeholder value, you need to update this
        }
        return payload

    def process(self, tilts: Dict[str, TiltHydrometer]):
        if not self.enabled:
            return

        if self.target_url is None or len(self.target_url) <= 11:
            return

        now = datetime.datetime.now()
        if now - self.data_last_sent > self.BIERBOT_SEND_FREQUENCY:
            target_dict = {
                'tilts': self.convert_tilts_to_list(tilts),
                'tiltbridge_junior': True,
            }
            payload = self.gen_json_payload(target_dict)
            try:
                r = requests.post(self.target_url, json=payload, timeout=5)
                response_data = json.loads(r.text)
                next_request_ms = response_data.get('next_request_ms')
                self.BIERBOT_SEND_FREQUENCY = datetime.timedelta(milliseconds=next_request_ms)
            except Exception as e:
                LOG.error(e)
                self.data_last_sent = now
                return

            if r.status_code != 200:
                LOG.error(f"Error sending data to Bierbot: {r.text}")
            else:
                LOG.info("Sent {} Tilt(s) to Bierbot".format(len(target_dict['tilts'])))
                LOG.info(f"Next send to Bierbot in: {self.BIERBOT_SEND_FREQUENCY} H:M:S")

            self.data_last_sent = now

if __name__ == "__main__":
    target = BierbotTarget()
    target.load_config()
