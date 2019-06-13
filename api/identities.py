from eth_utils.address import is_hex_address as is_valid_eth_address
from flask import request, jsonify

from models import db, Identity, IdentityRegistration
from request_helpers import validate_json, recover_identity


def register_endpoints(app):
    # End Point to save identity
    @app.route('/v1/identities', methods=['POST'])
    @recover_identity
    def save_identity(caller_identity):
        identity = Identity.query.get(caller_identity)
        if identity:
            return jsonify(error='identity already exists'), 403

        identity = Identity(caller_identity)
        db.session.add(identity)
        db.session.commit()

        return jsonify({})

    # End Point which returns payout info next to identity
    @app.route('/v1/identities/<identity_url_param>/payout', methods=['GET'])
    @recover_identity
    def payout_info(identity_url_param, caller_identity):
        if identity_url_param.lower() != caller_identity:
            return jsonify(error='no permission to access this identity'), 403

        record = IdentityRegistration.query.get(caller_identity)
        if not record:
            return jsonify(error='payout info for this identity not found'), \
                   404

        return jsonify({'eth_address': record.payout_eth_address, 'referral_code': record.referral_code})

    # End Point which creates or updates payout info next to identity
    @app.route('/v1/identities/<identity_url_param>/payout', methods=['PUT'])
    @validate_json
    @recover_identity
    def set_payout_info(identity_url_param, caller_identity):
        payload = request.get_json(force=True)

        payout_eth_address = payload.get('payout_eth_address', None)
        referral_code = payload.get('referral_code', None)

        if payout_eth_address is None:
            msg = 'missing payout_eth_address parameter in body'
            return jsonify(error=msg), 400

        if identity_url_param.lower() != caller_identity:
            msg = 'no permission to modify this identity'
            return jsonify(error=msg), 403

        if not is_valid_eth_address(payout_eth_address):
            msg = 'payout_eth_address is not in Ethereum address format'
            return jsonify(error=msg), 400

        record = IdentityRegistration.query.get(caller_identity)
        if record:
            record.update(payout_eth_address, referral_code)
            db.session.add(record)
        else:
            new_record = IdentityRegistration(
                caller_identity, payout_eth_address, referral_code
            )
            db.session.add(new_record)

        db.session.commit()
        return jsonify({})
