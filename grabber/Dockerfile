FROM python:3
ADD lacrosse.py /
RUN pip3 install influxdb
CMD [ "python", "-u", "lacrosse.py" ]