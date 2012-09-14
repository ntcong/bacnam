#!/usr/bin/env python
from flask import Flask
from bacnam import *
import string

app = Flask(__name__)


@app.route('/')
def api_root():
    return 'Welcome'


@app.route('/ip/')
def api_ip_usage():
    return 'You should be at /ip/<number>'


@app.route('/ip/<ip>')
def api_get_ip_latency(ip):
    ip = ipaddr.IPv4Address(ip)
    subnet_lists = get_subnet()
    for subnet in subnet_lists:
        if ip in ipaddr.IPv4Network(subnet):
            data = get_subnet_latency(subnet)
            break
    ping_hn, ping_hcm, diff = pickle.loads(data)
    if diff > 0:
        return "Subnet at HCM"
    else:
        return "Subnet at HN"


@app.route('/subnet/')
def api_subnet_usage():
    return 'You should be at /subnet/<number>'


@app.route('/subnet/<subnet>')
def api_get_subnet_latency(subnet):
    subnet = string.replace(subnet, '_', '/')
    if is_subnet_valid(subnet):
        return "Wrong subnet format"
    data = get_subnet_latency(subnet)
    ping_hn, ping_hcm, diff = pickle.loads(data)
    if diff > 0:
        return "Subnet at HCM"
    else:
        return "Subnet at HN"


if __name__ == '__main__':
    app.debug = True
    app.run()
