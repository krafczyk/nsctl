#!/bin/bash
set -e
nsctl create expressvpn --net --mount --sudo
nsctl net init expressvpn
nsctl net add macvlan expressvpn
nsctl net add veth expressvpn
nsctl net add port-forward expressvpn --ports 6000-6100
