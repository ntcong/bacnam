#!/usr/bin/env python
from bacnam import *
import random
api = __import__("bacnam-api")


# gi.country_code_by_addr('42.117.9.55')
# 'US'
ip_range_list = []



with open('IPBN.csv', 'r') as inf:
    for line in inf:
        data = line.split(',')
        code = 1 if data[4][1:-1] == 'VN' else 0
        ip_range_list.append([data[0][1:-1], data[1][1:-1], int(code)])


def get_random_IP(begin,end):
    begin = ipaddr.IPv4Address(begin)
    end = ipaddr.IPv4Address(end)
    diff = int(end)-int(begin)
    diff = random.randint(1,diff-1)
    return str(begin+diff)

def get_region(num):
    num = int(num)
    if num == 0:
        return 'HCM'
    elif num == 1:
        return 'HN'
    else:
        return 'UNKNOWN'


correct = 0
wrong = 0
read_env()
try:
    while 1:
        for begin,end,code in ip_range_list:
            for i in xrange(50):
                ip = get_random_IP(begin, end)
                rep = int(api.api_get_ip_latency(ip))
                print 'IP: %s, Location:%s, Result:%s' % (ip,get_region(code),get_region(rep)),
                if rep == code:
                    print '-- CORRECT'
                    correct += 1
                else:
                    print '-- WRONG'
                    wrong += 1
except KeyboardInterrupt:
    print 'Rate %s percent '% (correct*100/(correct+wrong))


