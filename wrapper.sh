#!/bin/bash

python -u ./print_stall.py &

python ./api.py &

wait -n

exit $?