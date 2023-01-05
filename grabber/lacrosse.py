"""
Retrieve your weather station's data from La Crosse Technology's cloud storage and adds to inlfuxdb

Credit for original code: https://github.com/keithprickett/lacrosse_weather and https://github.com/dbconfession78/py_weather_station
"""


import json
import requests
import time
import os
import sys
import traceback
from datetime import datetime, timedelta, timezone

from influxdb import InfluxDBClient
def datetime_to_int_seconds(dt_obj):
    """Converts a datetime object to integer seconds"""
    epoch_start = datetime(1970, 1, 1)
    return int((dt_obj - epoch_start).total_seconds())

def lacrosse_login(email, password):
    """
    Login to the La Crosse weather data and return the euser's valid token

    :param email: User's login e-mail address
    :param password: Users'a login password
    """

    url = "https://www.googleapis.com/" \
          "identitytoolkit/v3/relyingparty/verifyPassword?" \
          "key=AIzaSyD-Uo0hkRIeDYJhyyIg-TvAv8HhExARIO4"
    payload = {
        "email": email,
        "returnSecureToken": True,
        "password": password
    }
    r = requests.post(url, data=json.dumps(payload))
    body = r.json()
    token = body.get('idToken')

    if token is None:
        raise ConnectionError("Login Failed. Check credentials and try again")
    return token


def lacrosse_get_locations(token):
    """
    Query La Crosse server to return a list of user's locations

    :param token: Current, valid token for user session -- see `lacrosse_login`
    """

    url = "https://lax-gateway.appspot.com/" \
          "_ah/api/lacrosseClient/v1.1/active-user/locations"
    headers = {"Authorization": "Bearer " + token}
    r = requests.get(url, headers=headers)
    if r.status_code < 200 or r.status_code >= 300:
        raise ConnectionError("failed to get locations ()".
                              format(r.status_code))
    body = r.json()
    return body.get('items')


def lacrosse_get_devices(token, locations):
    """ Query La Crosse server to return a list of all devices for all locations

    :param token: Current, valid token for user session -- see `lacrosse_login`
    :param locations: List of lacrosse device locations
    """

    devices = list()
    for location in locations:
        url = "https://lax-gateway.appspot.com/" \
              "_ah/api/lacrosseClient/v1.1/active-user/location/"\
              + location['id']\
              + "/sensorAssociations?prettyPrint=false"
        headers = {"Authorization": "Bearer " + token}
        r = requests.get(url, headers=headers)
        if r.status_code < 200 or r.status_code >= 300:
            raise ConnectionError("failed to get weather data error: {}".format(r.status_code))
        body = r.json()
        if body:
            raw_devices = body.get('items')
            for device in raw_devices:
                sensor = device.get('sensor', {})
                devices.append({
                    "device_name": device.get('name').lower().replace(' ', '_'),
                    "device_id": device.get('id'),
                    "sensor_type_name": sensor.get('type', {}).get('name'),
                    "sensor_id": sensor.get('id'),
                    "sensor_field_names": [x for x in sensor.get('fields')
                                           if x.lower() != "notsupported"],
                    "location": location})
    return devices


def lacrosse_get_weather_data(token, device):
    """ Get the weather data for a single device on the La Crosse system

    :param token: Current, valid token for user session -- see `lacrosse_login`
    :param device: A device to query weather data from
    """
    fields_str = ",".join(device['sensor_field_names']) if device['sensor_field_names'] else None
    aggregates = "ai.ticks.1"
    
    now = datetime.now(timezone.utc)
    tz_dt = now.astimezone()
    #Go back records for 1 hour
    before = tz_dt - timedelta(days=1)
    start = str(before.isoformat())
    end = str(tz_dt.isoformat())
    start = "from={}&".format(start)
    end = "to={}&".format(end)

    #Use this if you want as much as you can grab
    #start = "from=&"
    #end = "to=&"
    
    print("DEVICE ID: " + device["device_id"])
    url = "https://ingv2.lacrossetechnology.com/" \
          "api/v1.1/active-user/device-association/ref.user-device.{id}/" \
          "feed?fields={fields}&" \
          "tz={tz}&" \
          "{_from}" \
          "{to}" \
          "aggregates={agg}&" \
          "types=spot".format(id=device["device_id"],
                              fields=fields_str, tz=os.getenv('TZ'),
                              _from=start, to=end, agg=aggregates)
    print("DATA URL: " + url)
    headers = {"Authorization": "Bearer " + token}
    r = requests.get(url, headers=headers)
    if r.status_code < 200 or r.status_code >= 300:
        raise ConnectionError("failed to get weather data error: {}".format(r.status_code))

    body = r.json()
    return body.get('ref.user-device.' + device['device_id']).get('ai.ticks.1').get('fields')

if __name__ == "__main__":
    try:
        email = os.getenv('EMAIL')
        password = os.getenv('PASSWORD')

        username= "weather"
        inpassword = "Welcome1"
        retention_policy = 'autogen'
        database = "weather"
        retention_policy = 'server_data'

        client =  InfluxDBClient(host='influxdb', port=8086, username=username, password=inpassword, database=database)
        while True:
            print("Logging in...")
            token = lacrosse_login(email, password)
            print("Getting locations...")
            locations = lacrosse_get_locations(token)
            print("Getting devices...")
            devices = lacrosse_get_devices(token, locations)
        
            for device in devices:
                if device['device_name'] == os.getenv('SENSOROUTSIDE'):
                    weather_data = lacrosse_get_weather_data(token, device)
                    series = []
                    for field in weather_data.keys():
                        for value in weather_data[field]['values']:
                            pointValues = {
                                "time": datetime.fromtimestamp(value['u'], tz=timezone.utc),
                                "measurement": field,
                                "fields": {
                                    "value": value['s'],
                                },
                                "tags": {
                                    "location": "outside",
                                },
                            }
                            series.append(pointValues)
                    client.write_points(series)
                if device['device_name'] == os.getenv('SENSORMAIN'):
                    weather_data = lacrosse_get_weather_data(token, device)
                    series = []
                    for field in weather_data.keys():
                        print(field)
                        for value in weather_data[field]['values']:
                            pointValues = {
                                "time": datetime.fromtimestamp(value['u'], tz=timezone.utc),
                                "measurement": ("inside-" + field),
                                "fields": {
                                    "value": value['s'],
                                },
                                "tags": {
                                    "location": "inside",
                                },
                            }
                            series.append(pointValues)
                    client.write_points(series)
            print("waiting...")
            time.sleep(30)
    except:
        print(traceback.format_exc())
        print("ERROR FOUND. KILLING SCRIPT TO RESTART CONTAINER.")
        sys.exit(1)


   

