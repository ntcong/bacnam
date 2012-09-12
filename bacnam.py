#!/usr/bin/env python
import ping
import socket
import redis
import ipaddr
import random
import cPickle as pickle
import argparse
import sys
import signal
import time
from multiprocessing import Pool

SERVER_ADDRESS = 'localhost'  # redis server location
SAMPLE_IP_SIZE = 5  # number of sample IP from a subnet
SAMPLE_PROB = 50  # number of IP in the beginning that have higher chance of online
MAX_TRYING = 10  # number of retrying before drop a subnet
MAX_POOL = 5  # max number of worker
TIMEOUT = 500  # ping timeout
REDIS_SUBNET_KEY = "list:subnet"  # redis key for store subnet list
REDIS_LATENCY_KEY = "queue:latency"  # redis key for store latency queue


redis_server = redis.Redis(SERVER_ADDRESS)
parser = argparse.ArgumentParser(description='Determine an IP address is located at HN or HCM')
parser.add_argument('-l', '--location', help='Server location (HN/HCM)', action="store", default='HN', metavar="HN/HCM")
parser.add_argument('--add-subnet', help='Add a subnet to processing queue', action="store", metavar="192.168.1.0/24")
args = parser.parse_args()


def init_worker():
    '''
    When system send Break/KeyboardInterrupt or SIGTERM, the subprocess
    hanged and doesn't cleanup properly for the main program to terminate
    Ignore SIGINT so the subprocess can do the cleanup to the parent
    '''
    signal.signal(signal.SIGINT, signal.SIG_IGN)


def get_subnet():
    return redis_server.lrange(REDIS_SUBNET_KEY, 0, -1)
    #return redis_server.blpop(REDIS_SUBNET_KEY)[1]


def add_subnet(subnet):
    redis_server.lpush(REDIS_SUBNET_KEY, subnet)


def add_to_queue(subnet, ip_list, latency):
    data = [str(subnet)]
    data.append(latency)
    for ip in ip_list:
        data.append(str(ip))
    data = pickle.dumps(data)
    redis_server.rpush(REDIS_LATENCY_KEY, data)


def get_queue():
    data = redis_server.blpop(REDIS_LATENCY_KEY)
    data = pickle.loads(data[1])  # data[0] is key, data[1] is the value
    return data


def get_random_IP(subnet):
    # IP start from 0->numhosts-1
    # ignore first and last IP in subnet
    num = random.randint(2, subnet.numhosts - 2)
    return subnet[num]


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


def scan_hcm_latency(data):
    # [subnet,hn_latency,IP_list]
    subnet = data[0]
    print 'Processing %s' % subnet
    ip_list = data[2:]
    total_latency = 0
    num = 0
    for ip in ip_list:
        print 'Trying %s' % ip,
        latency = get_latency(ip)
        print latency
        if latency != -1:
            total_latency += latency
            num += 1
    if num == 0:
        avg_latency = TIMEOUT
    else:
        avg_latency = total_latency / num
    # save data: key:subnet, data: (latency HN, latency HCM, HN-HCM)
    data.append(avg_latency)
    data = [data[1], avg_latency, data[1] - avg_latency]
    redis_server.set(subnet, pickle.dumps(data))


def scan_subnet(subnet):
    print 'Processing %s' % subnet
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
    add_to_queue(subnet, sample_IP, avg_latency)


def scan_hcm(id):
    scan_hcm_latency(get_queue())


def main():
    if args.add_subnet != None:
        try:
            ipaddr.IPv4Network(args.add_subnet)
        except ipaddr.AddressValueError:
            print '%s is not valid' % args.add_subnet
            return 0
        add_subnet(args.add_subnet)
        return
    if args.location == 'HN':
        while 1:
            worker = Pool(MAX_POOL, init_worker)
            subnet_list = get_subnet()
            try:
                for subnet in subnet_list:
                    worker.apply_async(scan_subnet, (subnet,))
                time.sleep(10)
            except KeyboardInterrupt:
                print 'Terminating...'
                worker.terminate()
                worker.join()
                return
            worker.close()
            worker.join()
    elif args.location == 'HCM':
        while 1:
            worker = Pool(MAX_POOL, init_worker)
            try:
                for i in range(MAX_POOL):
                    worker.apply_async(scan_hcm, (i,))
                time.sleep(10)
            except KeyboardInterrupt:
                print 'Terminating...'
                worker.terminate()
                worker.join()
                return
            worker.close()
            worker.join()


if __name__ == '__main__':
    main()
