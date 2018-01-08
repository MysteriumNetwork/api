from flask import Flask, request, render_template, jsonify
from flask_migrate import Migrate
from flask_sslify import SSLify
from werkzeug.debug import get_current_traceback
from functools import wraps
from models import db, Node, Session, NodeAvailability, Identity
from datetime import datetime
import helpers
import logging
from signature import (
    recover_public_address,
    ValidationError as SignatureValidationError
)
import base64
import settings


helpers.setup_logger()
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://{}:{}@{}/{}'.format(
    settings.USER, settings.PASSWD, settings.DB_HOST, settings.DB_NAME)

migrate = Migrate(app, db)


def validate_json(f):
    @wraps(f)
    def wrapper(*args, **kw):
        try:
            request.get_json(force=True)
        except:
            return jsonify({"error": 'payload must be a valid json'}), 400
        return f(*args, **kw)
    return wrapper


def decode_authorization_header(headers):
    # Authorization request header format:
    # Authorization: Signature <signature_base64_encoded>
    authorization = headers.get('Authorization')
    if not authorization:
        raise ValueError('missing Authorization in request header')

    authorization_parts = authorization.split(' ')
    if len(authorization_parts) != 2:
        raise ValueError('invalid Authorization header value provided, correct'
                         ' format: Signature <signature_base64_encoded>')

    authentication_type, signature_base64_encoded = authorization_parts

    if authentication_type != 'Signature':
        raise ValueError('authentication type have to be Signature')

    if signature_base64_encoded == '':
        raise ValueError('signature was not provided')

    try:
        signature_bytes = base64.b64decode(signature_base64_encoded)
    except TypeError as err:
        raise ValueError('signature must be base64 encoded: {0}'.format(err))

    try:
        return recover_public_address(
            request.data,
            signature_bytes,
        ).lower()
    except SignatureValidationError as err:
        raise ValueError('invalid signature format: {0}'.format(err))


def recover_identity(f):
    @wraps(f)
    def wrapper(*args, **kw):
        try:
            recovered_public_address = decode_authorization_header(request.headers)
        except ValueError as err:
            return jsonify(error=str(err)), 401

        kw['caller_identity'] = recovered_public_address
        return f(*args, **kw)

    return wrapper


@app.route('/', methods=['GET'])
def home():
    return render_template(
        'api.html',
    )


@app.route('/v1/node_register', methods=['POST'])
@validate_json
def node_register():
    payload = request.get_json(force=True)

    proposal = payload.get('service_proposal', None)
    if proposal is None:
        return jsonify(error='missing service_proposal'), 400

    node_key = proposal.get('provider_id', None)
    if node_key is None:
        return jsonify(error='missing provider_id'), 400

    node = Node.query.get(node_key)
    if not node:
        node = Node(node_key)

    node.ip = request.remote_addr
    node.connection_config = request.data
    node.updated_at = datetime.utcnow()
    db.session.add(node)
    db.session.commit()

    return jsonify({})


@app.route('/v1/proposals', methods=['GET'])
def proposals():
    node_key = request.args.get('node_key')

    if node_key:
        node = Node.query.get(node_key)
        nodes = [node] if node else []
    else:
        nodes = Node.query.all()

    service_proposals = []
    for node in nodes:
        service_proposals += node.get_service_proposals()

    return jsonify({'proposals': service_proposals})


# Node and client should call this endpoint each minute.
@app.route('/v1/sessions/<session_key>/stats', methods=['POST'])
@validate_json
def session_stats_create(session_key):
    payload = request.get_json(force=True)

    bytes_sent = payload.get('bytes_sent')
    bytes_received = payload.get('bytes_received')
    if bytes_sent < 0:
        return jsonify({'error': 'bytes_sent should not be negative'}), 400
    if bytes_received < 0:
        return jsonify({'error': 'bytes_received should not be negative'}), 400

    session = Session.query.get(session_key)
    if session is None:
        session = Session(session_key)
        session.client_ip = request.remote_addr

    session.client_bytes_sent = bytes_sent
    session.client_bytes_received = bytes_received
    session.client_updated_at = datetime.utcnow()

    db.session.add(session)
    db.session.commit()

    return jsonify({})


# Node call this function each minute.
@app.route('/v1/node_send_stats', methods=['POST'])
@validate_json
def node_send_stats():
    payload = request.get_json(force=True)
    node_key = payload.get('node_key', '')
    sessions = payload.get('sessions', [])

    return_values = []

    node = Node.query.get(node_key)
    if not node:
        return jsonify(error='node key not found'), 400

    # update node updated_at
    node.updated_at = datetime.utcnow()
    db.session.add(node)
    db.session.commit()

    # update sessions
    for se in sessions:
        session_key = se.get('session_key', '')
        bytes_sent = se.get('bytes_sent', 0)
        bytes_received = se.get('bytes_received', 0)

        # get session by key
        session = Session.query.get(session_key)
        is_session_valid = False

        if session:
            if session.established:
                if bytes_sent >= 0 and bytes_received >= 0:
                    session.node_bytes_sent = bytes_sent
                    session.node_bytes_received = bytes_received
                    session.node_updated_at = datetime.utcnow()
                    db.session.add(session)
                    db.session.commit()
                    is_session_valid = True

        return_values.append({
            'session_key': session_key,
            'is_session_valid': is_session_valid
        })

    # add record to NodeAvailability
    na = NodeAvailability(node_key)
    db.session.add(na)
    db.session.commit()

    return jsonify({
        'sessions': return_values
    })


# Client call this function each minute.
@app.route('/v1/client_send_stats', methods=['POST'])
@validate_json
def client_send_stats():
    payload = request.get_json(force=True)
    session_key = payload.get('session_key', '')
    bytes_sent = payload.get('bytes_sent', 0)
    bytes_received = payload.get('bytes_received', 0)

    # get session by key
    session = Session.query.get(session_key)
    is_session_valid = False

    if not session:
        return jsonify(error='session key not found'), 400

    if session:
        # TODO: add this checking as soon as send stats is implemented in node
        # if session.established:
        if bytes_sent >= 0 and bytes_received >= 0:
            session.client_bytes_sent = bytes_sent
            session.client_bytes_received = bytes_received
            session.client_updated_at = datetime.utcnow()
            db.session.add(session)
            db.session.commit()
            is_session_valid = True

    return jsonify({
        'session_key': session_key,
        'is_session_valid': is_session_valid
    })


# End Point to save identity
@app.route('/v1/identities', methods=['POST'])
@validate_json
def save_identity():
    payload = request.get_json(force=True)

    identity_arg = payload.get('identity', '').lower()
    identity = Identity.query.get(identity_arg)
    if identity:
        return jsonify(error='identity already exists'), 400

    identity = Identity(identity_arg)
    db.session.add(identity)
    db.session.commit()

    return jsonify({})


# End Point example which recovers public address from signed payload
@app.route('/v1/me', methods=['GET'])
@recover_identity
def test_signed_payload(caller_identity):
    return jsonify({
        'identity': caller_identity
    })


@app.errorhandler(404)
def method_not_found(e):
    return jsonify(error='unknown API method'), 404


@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify(error='method not allowed'), 405


@app.errorhandler(Exception)
def handle_error(e):
    track = get_current_traceback(
        skip=1,
        show_hidden_frames=True,
        ignore_system_exceptions=False
    )
    logging.error(track.plaintext)
    return jsonify(error=str(e)), 500


if __name__ == '__main__':
    sslify = SSLify(app)
    db.init_app(app)
    app.run(debug=True)
