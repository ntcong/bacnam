import ping
import socket
import redis
import ipaddr
import random
import cPickle as pickle
import argparse


SERVER_ADDRESS = 'localhost'
SAMPLE_IP_SIZE = 5
MAX_TRYING = 10
REDIS_SUBNET_KEY = "queue:subnet"
REDIS_QUEUE_KEY = "queue:latency"


redis_server = redis.Redis(SERVER_ADDRESS)
parser = argparse.ArgumentParser(description='test')
parser.add_argument('-l', '--location', help='123', action="store", default='HN', required=True)
args = parser.parse_args()

#load the subnet list


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
    redis_server.rpush(REDIS_QUEUE_KEY, data)


def get_queue():
    data = redis_server.blpop(REDIS_QUEUE_KEY)
    data = pickle.loads(data[1])  # data[0] is key, data[1] is the value
    return data


def get_new_sample_IP(subnet):
    # IP start from 0->numhosts-1
    # ignore first and last IP in subnet
    num = random.randint(2, subnet.numhosts - 2)
    return subnet[num]


def get_latency(IP):
    try:
        res = ping.Ping(str(IP), timeout=1000).do()
        if res is None:
            return -1
        else:
            return res
    except socket.error, e:
        print "Ping Error", e
        return -1


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
    tried = 0
    while len(sample_IP) < SAMPLE_IP_SIZE and tried < MAX_TRYING:
        IP = get_new_sample_IP(subnet)
        print 'Trying %s' % IP,
        latency = get_latency(IP)
        print latency
        if latency == -1:  # host is offline
            tried += 1
            continue
        else:
            total_latency += latency
            sample_IP.append(IP)
    if len(sample_IP) != 0:
        avg_latency = total_latency / len(sample_IP)
    else:
        avg_latency = 1000  # timeout value
    add_to_queue(subnet, sample_IP, avg_latency)


if args.location == 'HN':
    while 1:
        subnet_list = get_subnet()
        for subnet in subnet_list:
            scan_subnet(subnet)
elif args.location == 'HCM':
    while 1:
        scan_hcm_latency(get_queue())

