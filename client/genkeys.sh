#!/bin/sh
mkdir .ssh
openssl req -nodes -newkey rsa:2048 -keyout ~/.ssh/id_rsa -out ~/.ssh/id_rsa.csr -subj "/C=/ST=/L=/O=hasas/OU=/CN=hasas.zza.no"
openssl rsa -in .ssh/id_rsa -pubout 2>/dev/null > ~/.ssh/id_rsa.pub
