# Send tilt data to influxdb2

import datetime
import logging
import os
import json
import requests
import sentry_sdk

from typing import Dict
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS, WritePrecision
from influxdb_client.rest import ApiException
from TiltHydrometer import TiltHydrometer

LOG = logging.getLogger("tilt")

class InfluxDBTarget:
    VERSION = "1.0"

    INFLUXDB2_SEND_FREQUENCY = datetime.timedelta(seconds=15)

    def __init__(self):
        self.enabled = False
        self.data_last_sent = datetime.datetime.now()
        self.influxdb2_url = None
        self.influxdb2_token = None
        self.influxdb2_org = None
        self.influxdb2_bucket = None
        self.influxdb2_beername = None
        self.influxdb2_og = None

    def load_config(self):
        self.enabled = os.environ.get("INFLUXDB2_TARGET_ENABLED", "false").lower() == 'true'
        self.influxdb2_url = os.environ.get("INFLUXDB2_URL", "http://127.0.0.1:8086")
        self.influxdb2_token = os.environ.get("INFLUXDB2_TOKEN")
        self.influxdb2_org = os.environ.get("INFLUXDB2_ORG", "brewhouse")
        self.influxdb2_bucket = os.environ.get("INFLUXDB2_BUCKET", "fermenter")
        self.influxdb2_beername = os.environ.get("INFLUXDB2_BEERNAME", "Beer")
        self.influxdb2_og = float(os.environ.get("INFLUXDB2_OG"))
        self.tilt_color = os.environ.get("TILT_COLOR")

        valid_colors = ['red', 'green', 'black', 'purple', 'orange', 'blue', 'yellow', 'pink', 'any']

        if not self.enabled:
            LOG.info("Logging to InfluxDB Target is disabled")
        elif self.tilt_color.lower() not in [color.lower() for color in valid_colors]:
            LOG.error(f"Logging to Bierbot Target is enabled, but Tilt Color is not set to a valid color {valid_colors}")
        else:
            if not all([self.influxdb2_url, self.influxdb2_token, self.influxdb2_org, self.influxdb2_bucket, self.influxdb2_beername, self.influxdb2_og]):
                LOG.error("Logging to InfluxDB Target is enabled, but configuration is incomplete")
            else:
                LOG.info("Logging to InfluxDB Target is enabled")

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

        name  = os.environ.get("INFLUXDB2_BEERNAME", "Beer")
        influxdb2_og = float(os.environ.get("INFLUXDB2_OG", 1.000))

        color = tilt_data.get('color', '')
        name  = os.environ.get("INFLUXDB2_BEERNAME", "Beer")
        temp_fahrenheit = round(float(tilt_data.get('smoothed_temp', 0)), 1)
        temp_celsius = round(float((temp_fahrenheit - 32) * 5 / 9), 1)
        gravity = round(float(tilt_data.get('smoothed_gravity')), 3)
        original_gravity = round(float(os.environ.get("INFLUXDB2_OG", 1.000)), 3)
        alcohol_by_volume = round(float((original_gravity - gravity) * 131.25), 2)
        apparent_attenuation = round(float(((original_gravity - gravity) / (original_gravity - 1)) * 100), 1)
        plato = round(float(-616.868 + 1111.14 * gravity - 630.272 * gravity ** 2 + 135.997 * gravity ** 3), 1)
        timestamp = datetime.datetime.utcnow().isoformat()

        payload = {
            "measurement": "tilt",
            "tags": {
                "color": color,
                "name": name
            },
            "time": timestamp,
            "fields": {
                "temp_fahrenheit": temp_fahrenheit,
                "temp_celsius": temp_celsius,
                "gravity": gravity,
                "original_gravity": original_gravity,
                "alcohol_by_volume": alcohol_by_volume,
                "apparent_attenuation": apparent_attenuation,
                "plato": plato
            }
        }
        return payload

    def process(self, tilts: Dict[str, TiltHydrometer]):
        if not self.enabled:
            return

        now = datetime.datetime.now()
        if now - self.data_last_sent > self.INFLUXDB2_SEND_FREQUENCY:
            tilt_list = self.convert_tilts_to_list(tilts)

            if self.tilt_color == "any":
                tilt_list = tilt_list
            else:
                tilt_list = [tilt_data for tilt_data in tilt_list if tilt_data['color'].lower() == self.tilt_color.lower()]

            success_count = 0
            for tilt_data in tilt_list:
                payload = self.gen_json_payload(tilt_data)
                try:
                    client = InfluxDBClient(url=self.influxdb2_url, token=self.influxdb2_token)
                    write_api = client.write_api()
                    write_api.write(bucket=self.influxdb2_bucket, org=self.influxdb2_org, record=payload)
                except ApiException as e:
                    LOG.error(f"Error sending data to InfluxDB: {e}")
                    response_text = e.body if e.body else "No response received"
                    LOG.error(f"Response text: {response_text}")
                    self.data_last_sent = now
                    continue
                success_count += 1

            if success_count > 0:
                LOG.info(f"Sent {success_count} Tilt(s) to InfluxDB2")
                LOG.info(f"Next send to InfluxDB2 in: {self.INFLUXDB2_SEND_FREQUENCY} H:M:S")

            self.data_last_sent = now


if __name__ == "__main__":
    target = InfluxDBTarget()
    target.load_config()

