#!/bin/bash
set -e
#nsctl exec expressvpn /usr/sbin/expressvpnd --client-version 2.1.0 --client-build 7586
nsctl exec expressvpn /opt/expressvpn/bin/expressvpn-daemon
