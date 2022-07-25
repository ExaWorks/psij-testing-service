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

the last step is:
brew services start mongodb-community@6.0


This starts the service witch allows things to run locally:
cd ~/psi-j-testing-service; 
python3 src/psij/testing/service.py 

then you can see it at this url:
http://0.0.0.0:9909/summary.html



To populate the data i need to run psi-j-python:
you need to edit testing.conf first and, at a minimum, update the url to point to your server
server_url = http://0.0.0.0:9909

~/psi-j-python: pip3 install -r requirements-dev.txt
~/psi-j-python: make tests -- --upload-results


At LLNL, you will get this error: requests.exceptions.SSLError: HTTPSConnectionPool(host='testing.exaworks.org', port=443): Max retries exceeded with url: /result (Caused by SSLError(SSLCertVerificationError(1, '[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self signed certificate in certificate chain (_ssl.c:1056)')))
make: *** [tests] Error 1

the firewall basically does a MITM certificate switch
I don't remember the exact incantation, but you have to convince python to trust the root that signed the LLNL cert




