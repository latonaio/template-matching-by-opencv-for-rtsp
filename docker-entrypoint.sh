#!/bin/sh

python3.9 -m templatematching
/bin/sh -c "sleep 300"
curl -s -X POST localhost:10001/quitquitquit
