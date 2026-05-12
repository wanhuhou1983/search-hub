#!/bin/bash
cd /home/linhu/search-hub
export PATH=/home/linhu/.local/bin:/usr/local/bin:/usr/bin:/bin
python3 -m uvicorn main:app --host 0.0.0.0 --port 18081
