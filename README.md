profitbricks-cpu-autoscale
==========================
Example script for CPU autoscaling of ProfitBricks Servers.

On the servers runs a TCP inetd service that sends to the client the load                                                                                                   
average in the format "Load: 0.01 0.03 0.02".                                                                                                                               
This script retrieves the load average value from the inetd service                                                                                                         
periodically, calculcates the CPU utilization and if the CPU utilization is                                                                                                 
bigger than a threshold an additional CPU core is hot plugged into the server via the                                                                                                        
ProfitBricks API.                                                                                                                                                           
                        

