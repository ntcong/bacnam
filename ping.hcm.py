import ping
import socket
import redis
import ipaddr


SERVER_ADDRESS = 'localhost'
SAMPLE_IP_SIZE = 5
MAX_TRYING = 10
REDIS_QUEUE_KEY = "queue:latency"


redis_server = redis.Redis(SERVER_ADDRESS)


#load the subnet list


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


while 1:
    for subnet in subnet_list:
        scan_subnet(subnet)
