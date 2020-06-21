#!/bin/bash

scp -r -i ssh/id_rsa easyrsa/openvpn/* root@185.231.153.5:/etc/openvpn/server/
scp -r -i ssh/id_rsa easyrsa/openvpn/* root@62.113.113.199:/etc/openvpn/server/
