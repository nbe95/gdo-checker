#!/bin/bash

# Set up configuration.
stamp=`date '+%Y%m%d-%H%M'`
exp=30      # days to keep old log files

# Delete expired log files.
find ./logs/ -name "*.log" -type f -mtime +$exp -delete

# Run program and store output to log.
./sniffer.py > ./logs/$stamp.log
