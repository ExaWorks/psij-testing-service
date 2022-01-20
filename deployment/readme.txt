Contains files need to deploy the service.

To upgrade the container:
- decide on a release of the service
- update the version in RELEASE to '<major>.<minor>.<patch>'
- tag with 'v<major>.<minor>.<patch>' !important;
- run 'build.sh <major>.<minor>.<patch>' to build and push docker image
- on the deployment machine, stop the current container
- run 'run.sh <major>.<minor>.<patch>'

To upgrade the service with minimal downtime:
- exec into the container (do a 'docker ps' to figure out the id),
  then 'docker exec -it <container> /bin/bash'
- run 'update-psi-j-testing-service <major>.<minor>.<patch>'

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

It may also be necessary to restart nginx when the certificate
is updated by certbot. To do so, log into the server, get a shell
into the container (as above) and run 'service nginx restart'.