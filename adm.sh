#!/bin/bash
set -e

source nsctl_venv/bin/activate

nsctl create adm --net --mount --sudo
nsctl net init adm
nsctl net add veth adm --ns-subnet 192.168.4.0
