from flask import Flask, request, abort
from flask.ext.sqlalchemy import SQLAlchemy
import json

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hasas-db.sqlite'
db = SQLAlchemy(app)

class Sensor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    unit_type = db.Column(db.String(30))
    pubkey = db.Column(db.Text())


@app.route('/register-sensor', methods=['POST'])
def register_sensor():
    pubkey = request.form.get('pubkey')
    unit_type = request.form.get('unit_type')
    if not (pubkey and unit_type):
        abort(400)
    sensor = Sensor(unit_type=unit_type, pubkey=pubkey)
    db.session.add(sensor)
    db.session.commit()
    return json.dumps({
        'id': sensor.id,
        'checkin_url': 'https://hasas.zza.no/sensor-checkin',
        'certificate_url': 'https://hasas.zza.no/certificates/%d.crt' % (sensor.id)
    })


if __name__ == '__main__':
    db.create_all()
    app.run(debug=True)
