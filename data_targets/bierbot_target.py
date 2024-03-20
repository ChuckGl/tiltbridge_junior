# Send tilt data to Bierbot
# Payload docs: https://forum.bierbot.com/viewtopic.php?t=51

import datetime
import logging
import os
import json
import requests
import sentry_sdk

from typing import Dict
from TiltHydrometer import TiltHydrometer

LOG = logging.getLogger("tilt")

class BierbotTarget:
    VERSION = "1.0"

    BIERBOT_SEND_FREQUENCY = datetime.timedelta(seconds=15)

    def __init__(self):
        self.enabled = False
        self.target_url = None
        self.data_last_sent = datetime.datetime.now()

    def load_config(self):
        self.enabled = os.environ.get("BIERBOT_TARGET_ENABLED", "false").lower() == 'true'
        self.target_url = os.environ.get("BIERBOT_TARGET_URL")
        self.tilt_color = os.environ.get("TILT_COLOR")

        valid_colors = ['red', 'green', 'black', 'purple', 'orange', 'blue', 'yellow', 'pink', 'any']

        if not self.enabled:
            LOG.info("Logging to Bierbot Target is disabled")
        elif self.tilt_color.lower() not in [color.lower() for color in valid_colors]:
            LOG.error(f"Logging to Bierbot Target is enabled, but Tilt Color is not set to a valid color {valid_colors}")
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
    def gen_json_payload(tilt_data):
        if not tilt_data:
            print("No tilt data found")
            return {}  # Return an empty dictionary if tilt data is empty

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
            's_number_tilt_0': 123.456
        }
        return payload

    def process(self, tilts: Dict[str, TiltHydrometer]):
        if not self.enabled or self.target_url is None:
            return

        now = datetime.datetime.now()
        if now - self.data_last_sent > self.BIERBOT_SEND_FREQUENCY:
            tilt_list = self.convert_tilts_to_list(tilts)

            if self.tilt_color == "any":
                tilt_list = tilt_list
            else:
                tilt_list = [tilt_data for tilt_data in tilt_list if tilt_data['color'].lower() == self.tilt_color.lower()]

            success_count = 0
            for tilt_data in tilt_list:
                payload = self.gen_json_payload(tilt_data)
                try:
                    r = requests.post(self.target_url, json=payload, timeout=5)
                    response_data = json.loads(r.text)
                    next_request_ms = response_data.get('next_request_ms')
                    self.BIERBOT_SEND_FREQUENCY = datetime.timedelta(milliseconds=next_request_ms)

                    if r.status_code != 200:
                        LOG.error(f"Error sending data to Bierbot: {r.text}")
                        continue

                    success_count += 1

                except Exception as e:
                    LOG.error(e)
                    LOG.error("Error sending data to Bierbot")
                    self.data_last_sent = now
                    continue

            if success_count > 0:
                LOG.info(f"Sent {success_count} Tilt(s) to Bierbot")
                LOG.info(f"Next send to Bierbot in: {self.BIERBOT_SEND_FREQUENCY} H:M:S")

            self.data_last_sent = now

if __name__ == "__main__":
    target = BierbotTarget()
    target.load_config()
