#!/usr/bin/python
import os,sys
import json


from wsgiref.handlers import CGIHandler

from supersearch import app

CGIHandler().run(app)


