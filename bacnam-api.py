#!/usr/bin/env python
from flask import Flask, request
from bacnam import *
import string

app = Flask(__name__)


def check_auth(username, password):
    return username == 'admin' and password == '123456'


@app.route('/')
def api_root():
    return 'Welcome'


@app.route('/ip/')
def api_ip_usage():
    return 'You should be at /ip/<number>'


@app.route('/ip/<ip>')
def api_get_ip_latency(ip):
    if not is_ip_valid(ip):
        return "-1"
    ip = ipaddr.IPv4Address(ip)
    subnet_lists = get_subnet()
    data_list = {}
    for subnet in subnet_lists:
        if ip in ipaddr.IPv4Network(subnet):
            data = get_subnet_latency(subnet)
            data_list[subnet]= data
    if data_list == {}:
        return "-1"
    diff = 0
    data_list = sorted(data_list,reverse=True)
    for data in data_list:
        ping_hn, ping_hcm, diff = pickle.loads(data[1])
        if ping_hn == ping_hcm == TIMEOUT:
            continue
        else:
            break

    if diff > 0:
        return "0"
    elif diff < 0:
        return "1"
    else:
        return "-1"


@app.route('/subnet/')
def api_subnet_usage():
    return 'You should be at /subnet/<number>'


@app.route('/subnet/<subnet>', methods=['GET', 'POST'])
def api_get_subnet_latency(subnet):
    subnet = string.replace(subnet, '_', '/')
    if not is_subnet_valid(subnet):
        return "-1"
    if request.method == 'GET':  # get IP
        data = get_subnet_latency(subnet)
        ping_hn, ping_hcm, diff = pickle.loads(data)
        if diff > 0:
            return "0"
        else:
            return "1"
    elif request.method == 'POST':
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password) :
            return "Authentication Failed."
        add_subnet(subnet)
        return "Success"


if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0', port=80)
