import datetime
import logging
import os
import json
from typing import Dict
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS, WritePrecision

import sentry_sdk

from TiltHydrometer import TiltHydrometer
import requests

LOG = logging.getLogger("tilt")

class InfluxDBTarget:
    def __init__(self):
        self.enabled = False
        self.influxdb2_url = None
        self.influxdb2_token = None
        self.influxdb2_org = None
        self.influxdb2_bucket = None
        self.influxdb2_beername = None
        self.influxdb2_og = None

    def load_config(self):
        self.enabled = os.environ.get("INFLUXDB2_TARGET_ENABLED", "false").lower() == 'true'
        self.influxdb2_url = os.environ.get("INFLUXDB2_URL")
        self.influxdb2_token = os.environ.get("INFLUXDB2_TOKEN")
        self.influxdb2_org = os.environ.get("INFLUXDB2_ORG")
        self.influxdb2_bucket = os.environ.get("INFLUXDB2_BUCKET")
        self.influxdb2_beername = os.environ.get("INFLUXDB2_BEERNAME")
        self.influxdb2_og = float(os.environ.get("INFLUXDB2_OG", 1.000))

        if not self.enabled:
            LOG.info("Logging to InfluxDB Target is disabled")
        else:
            if not all([self.influxdb2_url, self.influxdb2_token, self.influxdb2_org, self.influxdb2_bucket, self.influxdb2_beername]):
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

    #@staticmethod
    def gen_influxdb_point(self, target_dict: Dict[str, any]) -> dict:
        tilt_dict = target_dict.get('tilts', [])
        if not tilt_dict:
            print("No tilt data found")
            return {}  # Return an empty dictionary if tilt data is empty

        tilt_data = tilt_dict[0]

        color = tilt_data.get('color', '')
        name = self.influxdb2_beername
        temp_fahrenheit = round(float(tilt_data.get('smoothed_temp', 0)), 1)
        temp_celsius = round(float((temp_fahrenheit - 32) * 5 / 9), 1)
        gravity = round(float(tilt_data.get('smoothed_gravity')), 3)
        original_gravity = round(float(self.influxdb2_og), 3)
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

        if not all([self.influxdb2_url, self.influxdb2_token, self.influxdb2_org, self.influxdb2_bucket]):
            return
        
        target_dict = {
            'tilts': self.convert_tilts_to_list(tilts),
            'tiltbridge_junior': True,
        }

        influxdb_point = self.gen_influxdb_point(target_dict)

        try:
            client = InfluxDBClient(url=self.influxdb2_url, token=self.influxdb2_token)
            write_api = client.write_api()
            write_api.write(bucket=self.influxdb2_bucket, org=self.influxdb2_org, record=influxdb_point)
            LOG.info("Sent tilt data to InfluxDB")
        except Exception as e:
            LOG.error(f"Error sending data to InfluxDB: {e}")

if __name__ == "__main__":
    target = InfluxDBTarget()
    target.load_config()
       

