#!/usr/bin/env python
import ping, socket
import redis
import ipaddr
import argparse

parser = argparse.ArgumentParser()
parser = argparse.ArgumentParser(description='test')
parser.add_argument('-l', '--location', help='123', action="store", default='HN', required=True)
args = parser.parse_args()
print args.location


print ipaddr.IPv4Address('192.0.2.1')

print ipaddr.IPv4Network('192.0.2.0/24')

redis_server = redis.Redis('localhost')
queue_key = "queue:latency"

t = redis_server.blpop(queue_key)

try:
    #ping.verbose_ping('118.69.251.121')
    delay = ping.Ping('118.69.251.120', timeout=2000).do()
except socket.error, e:
    print "Ping Error:", e

print 'delay is ', delay

