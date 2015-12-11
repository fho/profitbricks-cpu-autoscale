profitbricks-cpu-autoscale
==========================
This repository contains a script to demonstrate the idea of automatically
upscale the number of cores of ProfitBricks VMs depending on it's load.

The autoscale.py scripts periodically queries retrieves the load average of the
VMs from an inetd service. If the load becomes bigger than a defined maxium an
additional core is added to the VM via the ProfitBricks API.

Prerequiste
-----------
* Add a inetd service that runs the load.sh script on TCP port 777
* Configure the variables in autoscale.py to accord to your setup
