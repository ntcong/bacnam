#!/usr/bin/env python
import ipaddr
import random
from bacnam import *

list_ip = []
subnet_list = []

def is_subnet_valid(subnet):
    try:
        ipaddr.IPv4Network(subnet)
    except ipaddr.AddressValueError:
        return False
    return True


def is_ip_valid(ip):
    try:
        ipaddr.IPv4Network(ip)
    except ipaddr.AddressValueError:
        return False
    return True


def get_begin_random_IP(subnet):
    num = random.randint(2, SAMPLE_PROB)
    return subnet[num]


def get_latency(IP):
    try:
        res = ping.Ping(str(IP), timeout=TIMEOUT).do()
        if res is None:
            return -1
        else:
            return res
    except socket.error:
        print "Ping Error"
        sys.exit(1)


def test_ip(r):
    r = r.split()
    try:
        if is_subnet_valid(r[0]):
            return r[0]
        else:
            return None
    except IndexError:
        return None


def scan_subnet(subnet):
    subnet = ipaddr.IPv4Network(subnet)
    sample_IP = []
    total_latency = 0
    tried = 1
    while len(sample_IP) < SAMPLE_IP_SIZE and tried < 2 * MAX_TRYING:
        if tried < MAX_TRYING:
            IP = get_begin_random_IP(subnet)
        else:
            IP = get_random_IP(subnet)
        print 'Trying %s' % IP,
        latency = get_latency(IP)
        print latency
        if latency != -1:
            total_latency += latency
            sample_IP.append(IP)
        tried += 1
    if len(sample_IP) != 0:
        avg_latency = total_latency / len(sample_IP)
    else:
        avg_latency = TIMEOUT
    if avg_latency < 98:
        list_ip.append(str(subnet))


def main():
    worker = Pool(MAX_POOL, init_worker)
    try:
        for subnet in subnet_list:
            worker.apply_async(scan_subnet, (subnet,))
        time.sleep(5)
    except KeyboardInterrupt:
        print 'Terminating...'
        worker.terminate()
        worker.join()
        return
    worker.close()
    worker.join()

with open('new.xml', 'r') as inf:
    for line in inf:
        if line[-1] == '\n':
            subnet = line[:-1]
        else:
            subnet = line
        subnet_list.append(subnet)


main()


with open('bacnam3.sh', 'w') as ouf:
    for ip in list_ip:
        ouf.write('./bacnam.py --add-subnet %s\n' % ip)
