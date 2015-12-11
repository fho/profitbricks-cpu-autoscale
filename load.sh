#!/bin/sh

echo "CPUs: $(grep "processor" /proc/cpuinfo |wc -l)"
echo "Load: $(cut -d" " -f -3 /proc/loadavg)"
