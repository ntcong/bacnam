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


@app.route('/csv')
def apt_get_csv():
    auth = request.authorization
    if not auth or not check_auth(auth.username, auth.password) :
        return "Authentication Failed."
    result = ""
    with open("IPBN2.csv",'r') as inf:
        for line in inf:
            result += line
    return result

@app.route('/ip/')
def api_ip_usage():
    return 'You should be at /ip/<number>'


@app.route('/ip/<ip>')
def api_get_ip_latency(ip):
    if not is_ip_valid(ip):
        return "-1"
    subnet_lists = get_subnet(ip)
    ip = ipaddr.IPv4Address(ip)
    data_list = {}
    for subnet in subnet_lists:
        if ip in ipaddr.IPv4Network(subnet):
            data = get_subnet_latency(subnet)
            data_list[ipaddr.IPv4Network(subnet)]= data
    if data_list == {}:
        return "-1"
    diff = 0
    keys = data_list.keys()
    size = len(keys)
    for i in xrange(size):
        for j in xrange(size-1,i,-1):  # down from size to i+1
            if keys[j] in keys[i]:
                tmp = keys[i]
                keys[i] = keys[j]
                keys[j] = tmp
    datas = [data_list[key] for key in keys]
    for data in datas:
        if data is None:
            continue
        ping_hn, ping_hcm, diff = pickle.loads(data)
        if ping_hn == ping_hcm == TIMEOUT:
            continue
        else:
            break

    if diff > MIN_DIFFERENT:
        return "0"  # HCM
    elif diff < -MIN_DIFFERENT:
        return "1"   # HN
    else:
        return "0"  # return HCM for all unknown result by now
        #return "-1"


@app.route('/subnet/')
def api_subnet_usage():
    return 'You should be at /subnet/<number>'


@app.route('/subnet/<subnet>', methods=['GET', 'POST'])
def api_get_subnet_latency(subnet):
    subnet = string.replace(subnet, '_', '/')
    if not is_subnet_valid(subnet):
        return "-1"
    if request.method == 'GET':  # get subnet
        data = get_subnet_latency(subnet)
        if data is None:
            keys = []
            subnet_lists = get_subnet()
            isubnet = ipaddr.IPv4Network(subnet)
            for net in subnet_lists:
                if isubnet in ipaddr.IPv4Network(net):
                    keys.append(ipaddr.IPv4Network(net))
            size = len(keys)
            for i in xrange(size):
                for j in xrange(size-1,i,-1):  # down from size to i+1
                    if keys[j] in keys[i]:
                        tmp = keys[i]
                        keys[i] = keys[j]
                        keys[j] = tmp
            for key in keys:
                data = get_subnet_latency(str(key))
                if data is not None:
                    break
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
    read_env()
    app.debug = True
    app.run(host='0.0.0.0')
