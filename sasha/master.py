from flask import Flask, request, abort, render_template, flash, redirect, url_for, jsonify
from flask.ext.sqlalchemy import SQLAlchemy
from werkzeug import url_decode
import json
import threading
import time
import requests
import os
from datetime import datetime, timedelta

# Used to keep track of whether the main thread wants to quit
_terminate = False


class MethodRewriteMiddleware(object):

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        if '_method' in environ.get('QUERY_STRING', ''):
            args = url_decode(environ['QUERY_STRING'])
            method = args.get('_method')
            if method:
                method = method.encode('ascii', 'replace')
                environ['REQUEST_METHOD'] = method.upper()
        return self.app(environ, start_response)


app = Flask(__name__)
my_ip = requests.get('http://httpbin.org/ip').json()['origin']
print('Running on %s' % my_ip)
app.wsgi_app = MethodRewriteMiddleware(app.wsgi_app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///../db-dev.sqlite'
app.config['SECRET_KEY'] = 'supersecret'
app.config['SERVER_NAME'] = 'sasha.zza.no'
app.config['PREFERRED_URL_SCHEME'] = 'https'
db = SQLAlchemy(app)



def wants_json():
    best = request.accept_mimetypes.best_match(['application/json', 'text/html'])
    return best == 'application/json' and \
        request.accept_mimetypes[best] > \
        request.accept_mimetypes['text/html']


class Unit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    alias = db.Column(db.String(50), default='')
    description = db.Column(db.Text())
    ip = db.Column(db.String(46))
    unit_type = db.Column(db.String(30))
    state = db.Column(db.String(20), default='not-approved')
    last_checkin = db.Column(db.DateTime())
    certificate = db.Column(db.Text(), unique=True)
    actuators = db.Column(db.Text())
    sensors = db.Column(db.Text())
    associated_to_id = db.Column(db.Integer, db.ForeignKey('unit.id'))
    associated_to = db.relationship('Unit', remote_side=id, backref='associates')

    def to_json(self):
        return {
            'ip': self.ip,
            'id': self.id,
            'unit_type': self.unit_type,
            'certificate': self.certificate,
            'sensors': json.loads(self.sensors),
            'actuators': json.loads(self.actuators),
        }


class Subscription(db.Model):
    type = db.Column(db.String(30), primary_key=True)
    subscribers = db.Column(db.Text())


class SensorReading(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    unit_id = db.Column(db.Integer, db.ForeignKey('unit.id'))
    interface = db.Column(db.Integer)
    reading = db.Column(db.Float)


@app.route('/register-unit', methods=['POST'])
def register_unit():
    posted_data = request.json or {}
    csr = posted_data.get('csr')
    unit_type = posted_data.get('unit_type')
    sensors = posted_data.get('sensors', [])
    actuators = posted_data.get('actuators', [])
    description = posted_data.get('description', '')
    subscribe_to = posted_data.get('subscribe_to', [])
    print json.dumps(posted_data, indent=2)
    if not (csr and unit_type):
        abort(400)
    unit = Unit.query.filter_by(certificate=csr).first()
    if unit:
        if unit.state == 'rejected':
            return jsonify({
                'status': 403,
                'message': 'You have been rejected.'
                }), 403
    else:
        # New unit registered
        unit = Unit(
            unit_type=unit_type,
            certificate=csr,
            sensors=json.dumps(sensors),
            actuators=json.dumps(actuators),
            description=description,
        )
        db.session.add(unit)
        db.session.commit()
        print 'Adding new unit, subscribing to %s' % subscribe_to
        for unit_type_subscription in subscribe_to:
            subscription = Subscription.query.get(unit_type_subscription)
            if subscription:
                subscription.subscribers = json.dumps(json.loads(subscription.subscribers) + [unit.id])
                print 'Updated subscriptions, %s is now followed by %s' % (
                    unit_type_subscription, ', '.join(str(i) for i in json.loads(subscription.subscribers)))
            else:
                subscription = Subscription(type=unit_type_subscription, subscribers=json.dumps([unit.id]))
                print 'Created new subscription, %s now follows %s' % (unit.id, unit_type_subscription)
                db.session.add(subscription)
        db.session.commit()

    return jsonify({
        'id': unit.id,
        'checkin_url': url_for('unit_checkin', _external=True),
        'certificate_url': url_for('certificate', unit_id=unit.id, _external=True),
        'registry_url': url_for('registry', _external=True),
    })


@app.route('/')
def main():
    operational_units = Unit.query.filter(Unit.state!='not-approved').all()
    unapproved_units = Unit.query.filter(Unit.state=='not-approved').all()
    return render_template('main.html', operational_units=operational_units, unapproved_units=unapproved_units)


@app.route('/registry')
def registry():
    units = Unit.query.all()
    return jsonify({
        'units': [unit.to_json() for unit in units],
    })


@app.route('/units/<int:unit_id>', methods=['POST'])
def update_unit(unit_id):
    unit = Unit.query.get_or_404(unit_id)
    alias = request.form.get('alias', '')
    description = request.form.get('description', '')
    unit.alias = alias
    unit.description = description
    db.session.commit()
    if wants_json():
        return json.dumps({
            '_meta': {
                'status': 'OK',
            }
        })
    else:
        return redirect(url_for('main'))


@app.route('/checkin', methods=['POST'])
def unit_checkin():
    changes = False
    unit_ip = request.access_route[0]
    data = request.json or {}
    unit_id = data.get('unit_id')
    readings = data.get('readings', {})
    if not unit_id:
        abort(400)
    unit = Unit.query.get_or_404(unit_id)
    if unit.state == 'not-approved' or unit.state == 'rejected':
        abort(400)
    if unit.ip != unit_ip or not unit.last_checkin or unit.state == 'gone':
        changes = True
    if not unit.last_checkin:
        # First checkin for this unit, notify subscribers
        subscription = Subscription.query.get(unit.unit_type)
        if subscription:
            listeners_that_still_exist = []
            for listener_id in json.loads(subscription.subscribers):
                listener = Unit.query.get(listener_id)
                if listener:
                    # TODO: this code is going to act weird if there's several subscribers, should just choose the first one
                    unit.associated_to_id = listener_id
                    print 'Notifying %s about new %s unit %s' % (listener.alias or listener.id, unit.unit_type, unit.id)
                    notify_single_unit_of_registry_update(listener)
                    listeners_that_still_exist.append(listener_id)
            subscription.subscribers = json.dumps(listeners_that_still_exist)
            db.session.commit()
    unit.ip = unit_ip
    if unit.state == 'gone':
        print 'Unit %d (%s) is back up!' % (unit.id, unit.alias)
    unit.state = 'ok'
    unit.last_checkin = datetime.utcnow()
    db.session.commit()
    if changes:
        notify_units_of_registry_update()
    return jsonify({
        'status': 'OK!',
    })


def notify_units_of_registry_update():
    units = Unit.query.filter(Unit.state=='ok').all()
    headers = {'content-type': 'application/json'}
    for unit in units:
        notify_single_unit_of_registry_update(unit)


def notify_single_unit_of_registry_update(unit):
    try:
        target = 'http://%s/registry-updated' % unit.ip
        print('Notifying %s notified of registry update' % target)
        requests.post(target, data=json.dumps({
            'units': [u.to_json() for u in unit.associates],
        }), timeout=1, headers={'content-type': 'application/json'})
    except requests.exceptions.Timeout, requests.exceptions.ConnectionError:
        print('Unit %s does not respond to registry update, skipping...' % unit.id)




@app.route('/units/<int:unit_id>', methods=['DELETE'])
def delete_unit(unit_id):
    unit = Unit.query.get_or_404(unit_id)
    db.session.delete(unit)
    db.session.commit()
    flash('Unit deleted!', 'info')
    notify_units_of_registry_update()
    if wants_json():
        return jsonify({
            '_meta': {
                'status': 'OK!',
                'message': 'Unit deleted',
            }
        })
    else:
        return redirect(url_for('main'))


@app.route('/approve-unit/<int:unit_id>', methods=['POST'])
def approve_unit(unit_id):
    unit = Unit.query.get_or_404(unit_id)
    unit.alias = request.form.get('alias', '')
    unit.description = request.form.get('description', '')
    unit.state = 'approved'
    db.session.commit()
    flash('Accepted unit %s' % unit.id, 'info')
    return redirect(url_for('main'))


@app.route('/connect-units', methods=['POST'])
def connect_units():
    unit_id = request.form.get('unit_id')
    if not unit_id:
        abort(400)
    unit = Unit.query.get_or_404(unit_id)
    other_unit_id = request.form.get('other_unit', '')
    if other_unit_id:
        other_unit = Unit.query.get_or_404(other_unit_id)
        unit.associated_to = other_unit
        flash('%s succcessfully associated to %s' % (unit.alias, other_unit.alias), 'info')
    else:
        unit.associated_to = None
        flash('Removed associatation from %s' % unit.alias, 'info')
    notify_units_of_registry_update()
    db.session.commit()
    return redirect(url_for('main'))


@app.route('/reject-unit/<int:unit_id>', methods=['POST'])
def reject_unit(unit_id):
    unit = Unit.query.get_or_404(unit_id)
    unit.state = 'rejected'
    db.session.commit()
    flash('Unit %s rejected' % unit.id, 'info')
    return redirect(url_for('main'))


@app.route('/certificates/<int:unit_id>.crt')
def certificate(unit_id):
    unit = Unit.query.get_or_404(unit_id)
    if unit.state == 'rejected':
        abort(410)
    return os.urandom(30).encode('hex')


def watch_for_dead_units():
    time.sleep(30)
    while not _terminate:
        print '[housekeeping] Scanning for dead units...'
        changes = False
        units = Unit.query.filter((Unit.state=='ok') | (Unit.state=='approved')).all()
        for unit in units:
            if unit.last_checkin:
                now = datetime.utcnow()
                print "[housekeeping]", now - unit.last_checkin
                if now - unit.last_checkin > timedelta(minutes=1):
                    unit.state = 'gone'
                    print '[housekeeping] Unit %d (%s) considered dead, last heard from %s' % (unit.id, unit.alias, unit.last_checkin)
                    changes = True
        if changes:
            db.session.commit()
        time.sleep(30)


def main():
    ''' CLI entry-point for running master. '''
    db.create_all()

    housekeeping_thread = threading.Thread(target=watch_for_dead_units)
    housekeeping_thread.daemon = True
    housekeeping_thread.start()
    try:
        app.run(debug=True, host='0.0.0.0', port=80)
    except KeyboardInterrupt:
        _terminate = True
        raise
