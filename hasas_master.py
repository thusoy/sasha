from flask import Flask, request, abort, render_template, flash, redirect, url_for, jsonify
from flask.ext.sqlalchemy import SQLAlchemy
from werkzeug import url_decode
import json
import requests
import os
from datetime import datetime


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
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hasas-db.sqlite'
app.config['SECRET_KEY'] = 'supersecret'
app.config['SERVER_NAME'] = my_ip
app.config['PREFERRED_URL_SCHEME'] = 'https'
db = SQLAlchemy(app)



def wants_json():
    best = request.accept_mimetypes.best_match(['application/json', 'text/html'])
    return best == 'application/json' and \
        request.accept_mimetypes[best] > \
        request.accept_mimetypes['text/html']


class Unit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    alias = db.Column(db.String(50))
    description = db.Column(db.Text())
    ip = db.Column(db.String(46))
    unit_type = db.Column(db.String(30))
    state = db.Column(db.String(20), default='not-approved')
    last_checkin = db.Column(db.DateTime())
    certificate = db.Column(db.Text(), unique=True)
    actuators = db.Column(db.Text())
    sensors = db.Column(db.Text())

    def to_json(self):
        return {
            'ip': self.ip,
            'id': self.id,
            'unit_type': self.unit_type,
            'certificate': self.certificate,
            'sensors': json.loads(self.sensors),
            'actuators': json.loads(self.actuators),
        }


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
    sensors = posted_data.get('sensors')
    actuators = posted_data.get('actuators')
    print json.dumps(posted_data, indent=2)
    if not (csr and unit_type and sensors and actuators):
        abort(400)
    unit = Unit.query.filter_by(certificate=csr).first()
    if unit:
        if unit.state == 'rejected':
            return jsonify({
                'status': 403,
                'message': 'You have been rejected.'
                }), 403
    else:
        unit = Unit(
            unit_type=unit_type,
            certificate=csr,
            sensors=json.dumps(sensors),
            actuators=json.dumps(actuators),
        )
        db.session.add(unit)
        db.session.commit()
    return jsonify({
        'id': unit.id,
        'checkin_url': url_for('unit_checkin', _external=True),
        'certificate_url': url_for('certificate', unit_id=unit.id, _external=True),
        'registry_url': url_for('registry', _external=True),
    })


@app.route('/')
def main():
    approved_units = Unit.query.filter(Unit.state=='approved').all()
    unapproved_units = Unit.query.filter(Unit.state=='not-approved').all()
    return render_template('main.html', approved_units=approved_units, unapproved_units=unapproved_units)


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
    unit_ip = request.access_route[0]
    data = request.json or {}
    unit_id = data.get('unit_id')
    readings = data.get('readings')
    if not (unit_id and readings):
        abort(400)
    unit = Unit.query.get_or_404(unit_id)
    if not unit.state == 'approved':
        abort(400)
    unit.ip = unit_ip
    unit.last_checkin = datetime.utcnow()
    db.session.commit()
    notify_units_of_registry_update()
    return jsonify({
        'status': 'OK!',
    })


def notify_units_of_registry_update():
    units = Unit.query.all()
    headers = {'content-type': 'application/json'}
    for unit in units:
        try:
            target = 'http://%s/registry-updated' % unit.ip
            print('Notifying %s notified of registry update' % target)
            requests.post(target, data=json.dumps({
                'units': [u.to_json() for u in units],
            }), timeout=4)
        except:
            import traceback
            traceback.print_exc()
            print('Unit %s does not respond to registry update, skipping...' % unit.id)



@app.route('/units/<int:unit_id>', methods=['DELETE'])
def delete_unit(unit_id):
    unit = Unit.query.get_or_404(unit_id)
    db.session.delete(unit)
    db.session.commit()
    flash('Unit deleted!', 'info')
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
    unit.state = 'approved'
    db.session.commit()
    flash('Accepted unit %s' % unit.id, 'info')
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
    return os.urandom(30).encode('hex')


if __name__ == '__main__':
    db.create_all()
    app.run(debug=True, host='0.0.0.0', port=80)
