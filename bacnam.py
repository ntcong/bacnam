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
import os
from multiprocessing import Pool

REDIS_SERVER_ADDRESS = 'localhost'  # redis server location
SAMPLE_IP_SIZE = 5  # number of sample IP from a subnet
SAMPLE_PROB = 100  # number of IP in the beginning that have higher chance of online
MAX_TRYING = 50  # number of retrying before drop a subnet
MAX_POOL = 10  # max number of worker
TIMEOUT = 100  # ping timeout
REDIS_SUBNET_KEY = "list:subnet"  # redis key for store subnet list
REDIS_LATENCY_KEY = "queue:latency"  # redis key for store latency queue
MIN_DIFFERENT = 5  # min latency different between HN and HCM
REDIS_PASSWORD = 'foobared'

redis_server = None

def get_env(env):
    try:
        return os.environ[env]
    except KeyError:
        return None

def read_env():
    global REDIS_PASSWORD
    global REDIS_SERVER_ADDRESS
    global redis_server
    if get_env('REDIS_PASSWORD') != None:
        REDIS_PASSWORD = get_env('REDIS_PASSWORD')
    if get_env('REDIS_SERVER_ADDRESS') != None:
        REDIS_SERVER_ADDRESS = get_env('REDIS_SERVER_ADDRESS')
    redis.Redis(REDIS_SERVER_ADDRESS, password=REDIS_PASSWORD)

def init_worker():
    '''
    When system send Break/KeyboardInterrupt or SIGTERM, the subprocess
    hanged and doesn't cleanup properly for the main program to terminate
    Ignore SIGINT so the subprocess can do the cleanup to the parent
    '''
    signal.signal(signal.SIGINT, signal.SIG_IGN)


def get_subnet_latency(subnet):
    return redis_server.get(subnet)


def get_redis_key_from_subnet(subnet):
    subnet = subnet.split('/')
    ip = subnet[0]; mask = int(subnet[1])
    ip = ip.split('.')
    key = 'subnet'
    for i in xrange(mask/8):
        key += ':' + str(ip[i])
    return key

def get_subnet(subnet = None):
    if subnet == None:
        return redis_server.smembers(REDIS_SUBNET_KEY)
    else:
        ip = subnet.split('/')[0].split('.')
        key = 'subnet'
        result = set()
        for i in xrange(4):
            key += ':' + str(ip[i])
            result = result.union(redis_server.smembers(key))
        return result


def add_subnet(subnet):
    subnet_store = get_redis_key_from_subnet(subnet)
    redis_server.sadd(subnet_store, subnet)
    redis_server.sadd(REDIS_SUBNET_KEY, subnet)

def remove_subnet(subnet):
    subnet_store = get_redis_key_from_subnet(subnet)
    redis_server.srem(subnet_store, subnet)
    redis_server.srem(REDIS_SUBNET_KEY, subnet)


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
    if avg_latency == TIMEOUT:
        remove_subnet(subnet)
    else:
        add_to_queue(subnet, sample_IP, avg_latency)


def scan_hcm(id):
    scan_hcm_latency(get_queue())


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


def main():
    if args.add_subnet != None:
        if not is_subnet_valid(args.add_subnet):
            print '%s is not valid' % args.add_subnet
            return 0
        add_subnet(args.add_subnet)
        return
    if args.add_file != None:
        try:
            with open(args.add_file,'r') as inf:
                for line in inf:
                    if line[-1] == '\n':
                        subnet = line[:-1]
                    else:
                        subnet = line
                    if not is_subnet_valid(subnet):
                        print '%s is not valid' % subnet
                    add_subnet(subnet)
                return
        except IOError:
            print 'Invalid file'
            return
    if args.location == 'HN':
        while 1:
            worker = Pool(MAX_POOL, init_worker)
            print 'Getting list subnet...'
            subnet_list = get_subnet()
            print 'Done...'
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
    elif args.location == 'HCM':
        while 1:
            worker = Pool(MAX_POOL, init_worker)
            try:
                for i in range(MAX_POOL):
                    worker.apply_async(scan_hcm, (i,))
                time.sleep(5)
            except KeyboardInterrupt:
                print 'Terminating...'
                worker.terminate()
                worker.join()
                return
            worker.close()
            worker.join()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Determine an IP address is located at HN or HCM')
    parser.add_argument('-l', '--location', help='Server location (HN/HCM)', action="store", default='HN', metavar="HN/HCM")
    parser.add_argument('--add-subnet', help='Add a subnet to processing queue', action="store", metavar="192.168.1.0/24")
    parser.add_argument('--add-file', help='Add a list of subnets to processing queue from file', action="store", metavar="filename")
    read_env()
    args = parser.parse_args()

    main()
