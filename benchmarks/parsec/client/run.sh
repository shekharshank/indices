#!/bin/bash
while :
do
        /home/ubuntu/parsec-3.0/bin/parsecmgmt -a run -p $1 -i simlarge -n 4
done
