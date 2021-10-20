Contains files need to deploy the service.

There might be some manual work involved in initially 
getting SSL certs, but the following scheme is designed 
for automatic renewal:
- generate a self-signed certificate (you can use gen-cert.sh)
  (this is needed to get nginx running without too much messing
  with configuration files)
- start the container with run.sh <version>
- use certbot to get the actual cert; when it asks for the 
  webroot, point it to 'webroot'; this will place certs in 
  /etc/letsencrypt/live/<CN>/, so you'll need to carefully 
  symlink these into certs/certs/ssl.crt and 
  certs/private/ssl.key and restart the container; symlinking
  will not work outside of the volume mount, so the run script
  will automatically mount /etc/letsencrypt into the container 
  if it's there on the host

