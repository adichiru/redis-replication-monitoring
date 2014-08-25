#!/usr/bin/env python
#
# Copyright: Adi Chiru
# Functionality: mostly intended for Nagios but the only Nagios specific characteristic
#                is the exit codes; can be used in any other way...
# 2014-08-23 - Adi Chiru
#              - initial iteration
# 2014-08-25 - Adi Chiru
#              - fixing the multiple connects in the functions
#              - making sure the loop ends 2 seconds after the critical value is reached - makes no sense waiting longer

import sys
import argparse
import time
from decimal import Decimal
import math

REPL_DELAY_TEST_KEY = 'REPL_DELAY_TEST_KEY'
master_ts = 0
slave_ts = 0

STATE_OK = 0
STATE_WARNING = 1
STATE_CRITICAL = 2
STATE_UNKNOWN = 3

try:
    import redis
except ImportError:
    print ("WARNING: need to install redis python library." +
           "easy_install redis")
    sys.exit(STATE_WARNING)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-H', '--host',
                        required=True,
                        action='store',
                        dest='host',
                        type=str,
                        help='Host name of the redis instance.')
    parser.add_argument('-p', '--port',
                        required=True,
                        action='store',
                        dest='port',
                        type=int,
                        help='Port of the redis service.')
    parser.add_argument('-w', '--warning',
                        required=True,
                        action='store',
                        dest='max_sec_accepted_behind_master_warning',
                        type=int,
                        help='How many seconds behind master before warning notification.')
    parser.add_argument('-c', '--critical',
                        required=True,
                        action='store',
                        dest='max_sec_accepted_behind_master_critical',
                        type=int,
                        help='How many seconds behind master before critical notification.')

    args = parser.parse_args()

r_conn_slave = redis.StrictRedis(host=args.host, port=args.port)

def setts ():
    try:
        info_slave_dic = r_conn_slave.info()
        # get master's connection details:
        master_host = info_slave_dic['master_host']
        master_port = info_slave_dic['master_port']
    except Exception as e:
        print "Error when trying to get master's connection details: %s" % e
        sys.exit(STATE_WARNING)
    try:
        r_conn_master = redis.StrictRedis(host=master_host, port=master_port)
        # set a timestamp on master as value for the delay test key
        r_conn_master.delete(REPL_DELAY_TEST_KEY)
        master_ts = str(time.time())
        r_conn_master.set(REPL_DELAY_TEST_KEY, master_ts)
        #print "Setting ts: %s" % master_ts
    except Exception as e:
        print "Error when trying to write to master: %s" % e
        sys.exit(STATE_WARNING)
    return master_ts

def getts ():
    try:
        # get the value of the delay test key from slave
        slave_ts = str(r_conn_slave.get(REPL_DELAY_TEST_KEY))
        #print "Getting ts: %s" % slave_ts
    except Exception as e:
        print "Error when trying to read from slave: %s" % e
        sys.exit(STATE_WARNING)
    return slave_ts


master_ts = setts()
start_time = time.time()
timeout = time.time() + args.max_sec_accepted_behind_master_critical + 2
while True:
    slave_ts = getts()
    if ( time.time() > timeout ):
        print "Warning - Could not measure replication time. Slave may be %s seconds behind master (> %s sec)." % (timeout, args.max_sec_accepted_behind_master_warning)
        sys.exit(STATE_WARNING)
    elif ( slave_ts == master_ts ):
        end_time = time.time()
        break
delay = Decimal(end_time) - Decimal(start_time)
seconds_behind_master = math.ceil(delay*10000)/10000

if ( args.max_sec_accepted_behind_master_warning <= seconds_behind_master < args.max_sec_accepted_behind_master_critical ):
    print "Warning - Replication is slow: slave is %s seconds behind master (> %s sec)." % (seconds_behind_master, args.max_sec_accepted_behind_master_warning)
    sys.exit(STATE_WARNING)
elif ( seconds_behind_master > args.max_sec_accepted_behind_master_critical ):
    print "Critical! Replication problems: slave is %s seconds behind master (> %s sec)." % (seconds_behind_master, args.max_sec_accepted_behind_master_critical)
    sys.exit(STATE_CRITICAL)

print "Replication is OK. Slave is %s seconds behind master (< %s sec)." % (seconds_behind_master, args.max_sec_accepted_behind_master_warning)
sys.exit(STATE_OK)

# end of script