#!/usr/bin/python
# -*- coding: utf-8 -*-

import requests
import os
import sys
import json
import time
import importlib
import random
import threading
import argparse
import flask

def load_class_from_module(importstring):
    module_name, class_name = importstring.rsplit('.', 1)
    module = importlib.import_module(module_name)
    klass = getattr(module, class_name)
    return klass


class Client(object):

    def __init__(self, master, config_file):
        # Read from config.ini / pub- and priv-key files etc ??
        self.id = None
        self.terminate = False
        self.app = flask.Flask(__name__)
        self.unit_type = None
        self.checkin_frequency = None
        self.priv_key = ".ssh/id_rsa"
        self.certificate = None

        # setup url handlers
        self.configure_url_routes()

        # Replace with NFC discovery ??
        self.register_url = "http://%s/register-unit" % master
        self.checkin_url = None
        self.registry_url = None
        self.registry = []

        # Read config.ini
        with open(config_file) as config_fh:
            props = json.load(config_fh)

        self.unit_type = props['unit_type']
        self.checkin_frequency = props['checkin_frequency']

        self.actuators = {}
        for interface, actuator_class in props.get("actuators", {}).items():
            klass = load_class_from_module(actuator_class)
            self.actuators[interface] = klass(interface)

        self.sensors = {}
        for interface, sensor_class in props.get("sensors", {}).items():
            klass = load_class_from_module(sensor_class)
            self.sensors[interface] = klass(interface)


    def tear_down(self):
        pass


    def setup(self):
        with open(os.path.expanduser(os.path.join('~', '.ssh', 'id_rsa.csr'))) as csr_fh:
            csr = csr_fh.read()

        payload = {
            'unit_type': self.unit_type,
            'csr': csr,
            'sensors': [{
                'id': interface,
                'data': value.describe()
                } for interface, value in self.sensors.items()],
            'actuators': [{
                'id': interface,
                'data': value.describe()
                } for interface, value in self.actuators.items()]
        }

        headers = {'Content-Type': 'application/json'}
        r = requests.post(self.register_url, data=json.dumps(payload), headers=headers)
        if not r.ok:
            print 'Handshake with master failed, terminating...'
            sys.exit(1)
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
        while not self.terminate:
            payload = {
                'unit_id': self.id,
                'readings': {
                    interface: sensor.read()
                for interface, sensor in self.sensors.items()}
            }
            headers = {'Content-Type': 'application/json'}

            # Throws error on timeout, must have fallback!
            try:
                requests.post(self.checkin_url, data=json.dumps(payload), timeout=5, headers=headers)
                print "%s sent to %s" % (payload, self.checkin_url)
                backoff = 0
            except requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout:
                print "request timed out"
                backoff += 1



            sleeptime = min(self.checkin_frequency * 2**backoff, 60*15)
            time.sleep(sleeptime)
        print('Got terminate signal, stopping...')


    def configure_url_routes(self):
        """ Registers url routes on `self.app`. By convention, keep methods that are hit by HTTP
        prefixed with `http_`.
        """
        self.app.add_url_rule('/actuator/<actuator_id>', 'run_actuator', self.http_run_actuator, methods=['POST'])
        self.app.add_url_rule('/registry-updated', 'registry_update', self.registry_update, methods=["POST"])


    def http_registry_update(self):
        return flask.jsonify({
            'status': 'OK',
        })


    def http_run_actuator(self, actuator_id):
        actuator = self.actuators.get(actuator_id)
        if not actuator:
            abort(400)
        payload = flask.request.json or {}
        action = payload.get('action')
        args = payload.get('args', [])
        kwargs = payload.get('kwargs', {})
        if not action and (args or kwargs):
            abort(400)
        actuator.actuate(action, *args, **kwargs)


    def read(self):
        return [{
            'interface': 0,
            'value': random.random()*100
        }]


class LightBulbClient(Client):
    """Controll associated light bulbs"""

    def __init__(self, *args, **kwargs):
        super(LightBulbClient, self).__init__(*args, **kwargs)
        self.light_bulbs = []
        self.light_on = False
        self.listener = self.get_piface_switch_event_listener()
        self.listener.activate()

    def tear_down(self):
        self.listener.deactivate()

    def broadcast_light_change(self):
        """Message all associated light bulbs to turn on / off based on parameter light_on"""
        payoad = {
            "action": "SET_LIGHT",
            "kwargs": {
                "light_on": bool(self.light_on)
            }
        }
        headers = {'Content-Type': 'application/json'}

        for light_bulb in self.light_bulbs:
            requests.post(light_bulb, data=json.dumps(payoad), headers=headers)

        print "Turned %s the associated light bulbs." % ("on" if self.light_on else "off")


    def http_registry_update(self):
        light_bulbs = []
        payload = flask.request.json or {}
        for unit in payload.get('units', []):
            if unit.get('unit_type') == "LIGHT_BULB":
                for actuator in unit.get('actuators', []):
                    if actuator["data"].get('type') == "LIGHT_BULB":
                        light_bulbs.append('http://%s/actuator/%s' % (unit['ip'], actuator['id']))

        self.light_bulbs = light_bulbs

        return super(LightBulbClient, self).registry_update()

    def get_piface_switch_event_listener(self):
        import pifacecad
        cad = pifacecad.PiFaceCAD()
        listener = pifacecad.SwitchEventListener(chip=cad)
        for i in xrange(8):
            listener.register(i, pifacecad.IODIR_FALLING_EDGE, self.piface_switch_event_handler)
        return listener


    def piface_switch_event_handler(self, event):
        if event.pin_num == 0:
            self.toggle_lights()
        else:
            print "Ignored piface event for interface %d" % event.pin_num


    def toggle_lights(self):
        self.light_on = not self.light_on
        import pifacecad
        cad = pifacecad.PiFaceCAD()
        cad.lcd.backlight_on() if self.light_on else cad.lcd.backlight_off()
        self.broadcast_light_change()

def parse_args():
    parser = argparse.ArgumentParser(prog='hasas_client')
    parser.add_argument('master',
        metavar='<master>',
        default='hasas.zza.no')
    parser.add_argument('-c', '--config',
        metavar='<config-file>',
        default='config.json')
    return parser.parse_args()


def main():
    args = parse_args()
    with open(args.config) as config_fh:
        config = json.load(config_fh)
        client_class_name = config.get('client_class', 'hasas_client.Client')
        client_class = load_class_from_module(client_class_name)
    client = client_class(args.master, args.config)
    client.setup()
    checkin = threading.Thread(target=client.do_checkins)

    checkin.start()
    client.app.run(port=80, host='0.0.0.0', debug=True)
    client.terminate = True
    client.tear_down()
