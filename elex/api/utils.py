"""
Utility functions to record raw election results and handle low-level HTTP interaction with the
Associated Press Election API.
"""
from __future__ import print_function
import datetime
import elex
import json
import os
import requests
import sys
import six
import time

from pymongo import MongoClient
from xml.dom.minidom import parseString

class UnicodeMixin(object):
    """
    Python 2 + 3 compatibility for __unicode__
    """
    if sys.version_info > (3, 0):
        __str__ = lambda x: x.__unicode__()
    else:
        __str__ = lambda x: six.text_type(x).encode('utf-8')


def write_recording(payload):
    """
    Record a timestamped version of an Associated Press Elections API data download.

    Presumes JSON at the moment.
    Would have to refactor if using XML or FTP.
    FACTOR FOR USE; REFACTOR FOR REUSE.

    :param payload:
        JSON payload from Associated Press Elections API.
    """
    recorder = os.environ.get('ELEX_RECORDING', False)
    if recorder:
        timestamp = int(time.mktime(datetime.datetime.now().timetuple()))
        if recorder == u"mongodb":
            MONGODB_CLIENT = MongoClient(os.environ.get('ELEX_RECORDING_MONGO_URL', 'mongodb://localhost:27017/'))
            MONGODB_DATABASE = MONGODB_CLIENT[os.environ.get('ELEX_RECORDING_MONGO_DB', 'ap_elections_loader')]
            collection = MONGODB_DATABASE.elex_recording
            collection.insert({"time": timestamp, "data": payload})
        elif recorder == u"flat":
            recorder_directory = os.environ.get('ELEX_RECORDING_DIR', '/tmp')
            with open('%s/ap_elections_loader_recording-%s.json' % (recorder_directory, timestamp), 'w') as writefile:
                writefile.write(json.dumps(payload))


def api_request(path, **params):
    """
    Function wrapping Python-requests
    for making a request to the AP's
    elections API.

    A properly formatted request:
    * Modifies the BASE_URL with a path.
    * Contains an API_KEY.
    * Returns a response object.

    :param **params:
        Extra parameters to pass to `requests`.
    """
    if not params.get('apiKey', None):
        if elex.API_KEY != '':
            params['apiKey'] = elex.API_KEY
        else:
            params['apiKey'] = None

    if not params['apiKey']:
        raise KeyError('Oops! You have not exported an AP_API_KEY variable.')

    params['format'] = 'json'
    response = requests.get(elex.BASE_URL + path, params=params)
    if response.ok:
        write_recording(response.json())

    # When response is 403, take emergency action and write to stderr
    if response.status_code == 403:
        messagedom = parseString(response.content)
        message = messagedom.getElementsByTagName('Message')[0].childNodes[0].data
        print('ELEX ERROR: %s (url: %s)' % (message, response.url), file=sys.stderr)

    return response
