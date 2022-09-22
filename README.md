# psi-j-testing-service

# make virtual environment
virtualvenv psi
source psi/bin/activate

# install some things.

pip3 install -r requirements.txt

cd ~/psi-j-testing-service/src/psij/testing
python3 service.py

# you will need mongoDB, follow the instructions here, it takes a while to install.
https://www.mongodb.com/docs/manual/tutorial/install-mongodb-on-os-x/

On Mac OS X, the last step is:
brew services start mongodb-community@6.0



Creating A Local Dev Environment
------------------------------------------------------
This starts the service witch allows things to run locally:
cd ~/psi-j-testing-service; 
python3 src/psij/testing/service.py 

then you can see it at this url:
http://127.0.0.1:9909/summary.html



To populate the data i need to run psi-j-python:
Edit testing.conf first and, at a minimum, update the url to point to your server
server_url = http://0.0.0.0:9909

~/psi-j-python: pip3 install -r requirements-dev.txt
~/psi-j-python: make tests -- --upload-results


Restoring a mongodump DB:
You'll want to get a full dump, that way you can play with the data:

First untar these:
mongodump-psij.tar
mongodump-sdk.tar.gz

mongorestore dump/



