#!/usr/bin/python
import os,sys
import json


from wsgiref.handlers import CGIHandler

from log import app


CGIHandler().run(app)


