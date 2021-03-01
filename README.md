# La Crosse, Grafana and InfluxDB
Docker-compose environment that grabs La Crosse Weather cloud data and displays within a Grafana dashboard

Credit for original code: https://github.com/keithprickett/lacrosse_weather and https://github.com/dbconfession78/py_weather_station

## Steps

### Needed Variables
- Either rename sample.env to .env
- Create individual env variables
    - EMAIL
    - PASSWORD
    - SENSORMAIN
    - SENSOROUTSIDE
- Edit docker-compose file directly

### Run
`docker-compose up -d`

## Access
Access Grafana (admin\admin)
http://dockerhost:3000/

- Dashboard: http://dockerhost:3000/d/FTJglUyGz (Weather)

## Containers

### Grabber
Python script that runs every 30 seconds to pull from La Crosse cloud and write to InfluxDB

### InfluxDb
InfluxDB with `weather` database being created and used

### Grafana
Grafana with InfluxDB datasource and dashboard (Weather) created
