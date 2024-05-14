#!/bin/bash

l=$1
f=$2
a=$3
k=$4
cd /home/$USER/Desktop/Files
python3 -u SSHServerEncryptionScript.py -op $l -file $f -attr $a -key $k