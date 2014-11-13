#!/bin/sh

set -e

test -d ~/.ssh || mkdir ~/.ssh
openssl req -nodes -newkey rsa:2048 -keyout ~/.ssh/id_rsa -out ~/.ssh/id_rsa.csr -subj "/C=/ST=/L=/O=sasha/OU=/CN=sasha.zza.no"
openssl rsa -in ~/.ssh/id_rsa -pubout 2>/dev/null > ~/.ssh/id_rsa.pub
