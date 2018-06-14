# redis-replication-monitoring

This is a solution to monitor the status of the Redis replication.

The main issue is that Redis replication does not give you an idea of how far behind a slave may be from its master (at least at the time of writing this script).

I created this script after several discussions on the official Redis mailing list that lead me to the conclusion that this is actually missing from Redis.

This script is supposed to be executed by monitoring solutions like Nagios or Zabbix.
