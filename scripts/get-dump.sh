#!/bin/bash

# this script was meant to be run on the server
# it will get you the database dump that you can use to populate your local database.
sudo docker exec -it service-psij mongodump --out=sc-dump
sudo docker cp service-psij:~/sc-dump ~/sc-dump

tar -cf sc-dump.tar sc-dump

sudo rm -rf sc-dump
ls -l
