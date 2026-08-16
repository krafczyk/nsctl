#!/bin/bash
set -e

source nsctl_venv/bin/activate

nsctl exec --as-user matthew adm ssh x630773@050slurmlogin.research.na.admworld.com -Y
