#!/bin/bash
set -e

source nsctl_venv/bin/activate

nsctl exec adm openconnect https://myvpn.adm.com
