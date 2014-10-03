#!/usr/bin/python

import requests
import os
import sys
import json
import time
import random
import threading
import argparse
import flask

class Client(object):

    def __init__(self, master):
        # Read from config.ini / pub- and priv-key files etc ??
        self.id = None
        self.unit_type = None
        self.checkin_frequency = None
        self.priv_key = ".ssh/id_rsa"
        self.certificate = None

        # Replace with NFC discovery ??
        self.register_url = "http://%s/register-unit" % master
        self.checkin_url = None
        self.registry_url = None
        self.registry = []

        # must import file / package / something
        self.interfaces = InterfaceList()

        # Read config.ini
        with open(os.path.join(os.path.dirname(__file__), 'config.json')) as config_fh:
            props = json.load( config_fh )

        self.unit_type = props['unit_type']
        self.checkin_frequency = props['checkin_frequency']
        #self.interfaces = propes['interfaces']



    def setup(self):
        with open(os.path.expanduser(os.path.join('~', '.ssh', 'id_rsa.csr'))) as csr_fh:
            csr = csr_fh.read()

        payload = {
            'unit_type': self.unit_type,
            'csr': csr
        }
        r = requests.post(self.register_url, data=payload)
        response = r.json()

        self.certificate_url = response['certificate_url']
        self.checkin_url = response['checkin_url']
        self.registry_url = response['registry_url']
        self.id = response['id']

        self.collect_certificate()
        self.populate_registry()

    def collect_certificate(self, backoff_interval=1):
        if backoff_interval > 9 or backoff_interval < 1:
            return

        for _ in xrange (backoff_interval):
            print "Requesting certificate from %s" % (self.certificate_url)
            r = requests.get(self.certificate_url)
            if r.status_code == requests.codes.ok:
                self.certificate = r.text
                print "Received certificate from %s" % (self.certificate_url)
                return
            else:
                time.sleep(backoff_interval)
        if not self.certificate:
            self.collect_certificate(backoff_interval*2)

    def populate_registry(self):
        r = requests.get(self.registry_url, timeout=5)
        if r.status_code == requests.codes.ok:
            response = r.json()
            self.registry = response['units'];
        print "Found %d other devices" % len(self.registry)


    def add_to_registry(self, unit):
        pass


    def do_checkins(self):
        backoff = 0
        while True:
            payload = {
                'unit_id': self.id,
                'readings': self.read()
            }
            headers = {'Content-Type': 'application/json'}

            # Throws error on timeout, must have fallback!
            try:
                requests.post(self.checkin_url, data=json.dumps(payload), timeout=5, headers=headers)
                print "%s sent to %s" % (payload, self.checkin_url)
                backoff = 0
            except requests.exceptions.ConnectTimeout:
                print "request timed out"
                backoff += 1

            sleeptime = min(self.checkin_frequency * pow(2, backoff), 60*15)
            time.sleep(sleeptime)

    def do_listen(self):
        app = flask.Flask(__name__)

        @app.route('/')
        def main():
            return flask.jsonify({
                'response': 'Got it'
            })

        @app.route('/registry-updated', methods=["POST"])
        def registry_update():
            return flask.jsonify({
                'status': 'OK',
            })

        app.run(host="0.0.0.0", port=80)


    def read(self):
        return [{
            'interface': 0,
            'value': random.random()*100
        }]


def parse_args():
    parser = argparse.ArgumentParser(prog='hasas_client')
    parser.add_argument('master',
        metavar='<master>',
        default='hasas.zza.no')
    return parser.parse_args()


def main():
    args = parse_args()
    c = Client(args.master)
    print c.interfaces();
    return
    c.setup()
    checkin = threading.Thread(target=c.do_checkins)
    callback = threading.Thread(target=c.do_listen)

    checkin.start()
    callback.start()

if __name__ == '__main__':
    main()
