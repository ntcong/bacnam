#!/usr/bin/env python

from bacnam import *
subnet_list = get_subnet()


def get_region(num):
    num = int(num)
    if diff > MIN_DIFFERENT:
        return "US"  # HCM
    elif diff < -MIN_DIFFERENT:
        return "VN"   # HN
    else:
        return "US"  # return HCM for all unknown result by now

with open('IPBN2.csv', 'w') as ouf:
    for subnet in subnet_list:
        net = ipaddr.IPv4Network(subnet)
        data = get_subnet_latency(subnet)
        if data == None:
            continue
        ping_hn, ping_hcm, diff = pickle.loads(data)
        if int(diff) == 0:
            continue
        ouf.write('"%s","%s","%s","%s","%s","%s"\n' % ( \
            net[0], net[-1], int(net[0]), int(net[-1]), \
            get_region(diff), get_region(diff)))
