#!/bin/sh
cd "$(dirname "$0")"
python3 -m admin_core.server --port 8099
