from flask import Flask, request, abort, render_template, flash, redirect, url_for, jsonify
from flask.ext.sqlalchemy import SQLAlchemy
from werkzeug import url_decode
import json
import requests
import os


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
    pubkey = db.Column(db.Text(), unique=True)


class SensorReading(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    unit_id = db.Column(db.Integer, db.ForeignKey('unit.id'))
    interface = db.Column(db.Integer)
    reading = db.Column(db.Float)


@app.route('/register-unit', methods=['POST'])
def register_unit():
    csr = request.form.get('csr')
    unit_type = request.form.get('unit_type')
    if not (csr and unit_type):
        abort(400)
    unit = Unit.query.filter_by(pubkey=csr).first()
    if not unit:
        unit = Unit(unit_type=unit_type, pubkey=csr)
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
    units = Unit.query.all()
    return render_template('main.html', units=units)


@app.route('/registry')
def registry():
    units = Unit.query.all()
    return jsonify({
        'units': [{
            'ip': unit.ip,
            'id': unit.id,
            'unit_type': unit.unit_type,
        } for unit in units],
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
    unit.ip = unit_ip
    db.session.commit()
    return jsonify({
        'status': 'OK!',
    })



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


@app.route('/certificates/<int:unit_id>.crt')
def certificate(unit_id):
    return os.urandom(30).encode('hex')


if __name__ == '__main__':
    db.create_all()
    app.run(debug=True, host='0.0.0.0', port=80)
