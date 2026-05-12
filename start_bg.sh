#!/bin/bash
cd /home/linhu/search-hub
export PATH=/home/linhu/.local/bin:/usr/local/bin:/usr/bin:/bin
nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 18081 > /home/linhu/search-hub/uvicorn.log 2>&1 &
echo $!
