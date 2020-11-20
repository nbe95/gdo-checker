#!/bin/bash

# Set up configuration.
stamp=$(date '+%Y%m%d-%H%M')
log_path="/var/log/gdo-sniffer-kevelaer/"
exp=30      # days to keep old log files


# Create log directory if not yet existing.
mkdir -p $log_path

# Delete expired log files.
find $log_path -name "*.log" -type f -mtime +$exp -delete

# Run program and additionally store output to log file.
"/usr/local/src/gdo-sniffer-kevelaer/sniffer.py" $@ | tee ${log_path}${stamp}.log
