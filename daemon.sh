#!/bin/bash
PYTHONHTTPSVERIFY=0 python /var/www/cgi-bin/api/daemon-glycan.py
PYTHONHTTPSVERIFY=0 python /var/www/cgi-bin/api/daemon-protein.py
