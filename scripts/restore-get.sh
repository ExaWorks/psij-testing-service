#!/bin/bash

# run this script after running get-dump
# you will need to change the username below

scp -r aschwanden1@testing.exaworks.org:~/sc-dump.tar ~/sc-dump.tar
cd ~/
tar -xvf ~/sc-dump.tar

mongosh psi-j-testing-aggregator --eval "db.dropDatabase()"

mongorestore ~/sc-dump
