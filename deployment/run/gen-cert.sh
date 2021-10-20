#!/bin/bash

openssl req -x509 -newkey rsa:4096 -sha256 -days 3650 -nodes \
    -keyout certs/private/ssl.key -out certs/certs/ssl.crt -subj "/CN=example.com" \
    -addext "subjectAltName=DNS:example.com,DNS:www.example.net,IP:127.0.0.1"
