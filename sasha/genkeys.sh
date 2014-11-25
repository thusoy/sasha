#!/bin/sh

set -e

if [ $(id -u) -ne 0 ]; then
    echo "Need to be root to run this script!"
    exit 1
fi

test -d /etc/sasha || mkdir /etc/sasha
cd /etc/sasha
echo "Creating EC key..."
openssl ecparam -genkey -name prime256v1 -out privkey.pem
chmod 400 privkey.pem
echo "Generating CSR..."
openssl req -new -nodes -key privkey.pem -out csr.pem -sha256 -subj "/C=/ST=/L=/O=sasha/OU=/CN=sasha.zza.no"
