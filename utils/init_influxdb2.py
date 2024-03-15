from datetime import datetime
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS, WritePrecision

# Define InfluxDB connection parameters
INFLUXDB2_URL = "http://localhost:8086"
INFLUXDB2_TOKEN = "gmHXhCVjSdiVLrtMLXwB0cvM90C9-eb5JGL6hoMLm0a5ZxjUSEXmqtDUfEy3EyIPHUn8fIAOgjnW65sRpHqBgg=="
INFLUXDB2_ORG = "brewhouse"
INFLUXDB2_BUCKET = "fermenter"

# Define variables for testing data insertion
TILT_COLOR = "orange"
NAME = "Test Beer"
TEMP_FAHRENHEIT = 75.5
TEMP_CELSIUS = 24.2
GRAVITY = 1.014
ORIGINAL_GRAVITY = 1.061
ALCOHOL_BY_VOLUME = 6.2
APPARENT_ATTENUATION = 75.0
PLATO = 12.5

# Create client
client = InfluxDBClient(url=INFLUXDB2_URL, token=INFLUXDB2_TOKEN)

# Create the "fermenter" bucket
buckets_api = client.buckets_api()
bucket = buckets_api.create_bucket(bucket_name=INFLUXDB2_BUCKET, org_id=INFLUXDB2_ORG)

# Write data
write_api = client.write_api(write_options=SYNCHRONOUS)
data_point = Point("tilt").tag("color", TILT_COLOR).tag("name", NAME) \
                          .field("temp_fahrenheit", TEMP_FAHRENHEIT) \
                          .field("temp_celsius", TEMP_CELSIUS) \
                          .field("gravity", GRAVITY) \
                          .field("original_gravity", ORIGINAL_GRAVITY) \
                          .field("alcohol_by_volume", ALCOHOL_BY_VOLUME) \
                          .field("apparent_attenuation", APPARENT_ATTENUATION) \
                          .field("plato", PLATO) \
                          .time(datetime.utcnow())
write_api.write(bucket=INFLUXDB2_BUCKET, org=INFLUXDB2_ORG, record=data_point, write_precision=WritePrecision.MS)

