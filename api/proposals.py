import settings
import helpers
import json
from flask import request, jsonify
from models import db, Node, ProposalAccessPolicy
from request_helpers import validate_json, restrict_by_ip, recover_identity
from identity_contract import IdentityContract
from queries import (
    filter_active_nodes,
    filter_active_nodes_by_service_type,
    filter_nodes_without_access_policies,
    filter_nodes_by_access_policy,
    filter_nodes_in_bounty_programme,
    filter_nodes_by_node_type
)


identity_contract = IdentityContract(
    settings.ETHER_RPC_URL,
    settings.IDENTITY_CONTRACT,
    settings.ETHER_MINING_MODE
)


def register_endpoints(app):
    @app.route('/v1/register_proposal', methods=['POST'])
    # TODO: remove deprecated route when it's not used anymore
    @app.route('/v1/node_register', methods=['POST'])
    @restrict_by_ip
    @validate_json
    @recover_identity
    def register_proposal(caller_identity):
        if settings.DISCOVERY_VERIFY_IDENTITY and \
                not identity_contract.is_registered(caller_identity):
            return jsonify(error='identity is not registered'), 403

        payload = request.get_json(force=True)

        proposal = payload.get('service_proposal', None)
        if proposal is None:
            return jsonify(error='missing service_proposal'), 400

        service_type = proposal.get('service_type', None)
        if service_type is None:
            return jsonify(error='missing service_type'), 400

        node_key = proposal.get('provider_id', None)
        if node_key is None:
            return jsonify(error='missing provider_id'), 400

        if node_key.lower() != caller_identity:
            message = 'provider_id does not match current identity'
            return jsonify(error=message), 403

        node = Node.query.get([node_key, service_type])
        if not node:
            node = Node(node_key, service_type)

        node.ip = request.remote_addr
        node.proposal = json.dumps(proposal)
        # add the column to make querying easier
        node.service_type = service_type

        access_policies = proposal.get('access_policies')
        if access_policies:
            for policy_data in access_policies:
                id = policy_data['id']
                source = policy_data['source']
                db.session.merge(ProposalAccessPolicy(node_key, id, source))

        node_type = helpers.parse_node_type_from_proposal(proposal)
        if node_type:
            node.node_type = node_type

        node.mark_activity()
        db.session.add(node)
        db.session.commit()

        return jsonify({})

    @app.route('/v1/unregister_proposal', methods=['POST'])
    @restrict_by_ip
    @validate_json
    @recover_identity
    def unregister_proposal(caller_identity):
        payload = request.get_json(force=True)

        service_type = payload.get('service_type', 'openvpn')

        node_key = payload.get('provider_id', None)
        if node_key is None:
            return jsonify(error='missing provider_id'), 400

        if node_key.lower() != caller_identity:
            message = 'provider_id does not match current identity'
            return jsonify(error=message), 403

        node = Node.query.get([node_key, service_type])
        if not node:
            return jsonify({}), 404

        node.mark_inactive()
        db.session.commit()

        return jsonify({})

    @app.route('/v1/proposals', methods=['GET'])
    def proposals():
        service_type = request.args.get('service_type', 'openvpn')
        if service_type == "all":
            nodes = filter_active_nodes()
        else:
            nodes = filter_active_nodes_by_service_type(service_type)

        node_key = request.args.get('node_key')
        if node_key:
            nodes = nodes.filter_by(node_key=node_key)

        if request.args.get('access_policy') != '*':
            id = request.args.get('access_policy[id]')
            source = request.args.get('access_policy[source]')
            if id or source:
                nodes = filter_nodes_by_access_policy(nodes, id, source)
            else:
                nodes = filter_nodes_without_access_policies(nodes)

        if request.args.get('bounty_only') == 'true':
            nodes = filter_nodes_in_bounty_programme(nodes)

        node_type_arg = request.args.get('node_type')
        if node_type_arg:
            nodes = filter_nodes_by_node_type(nodes, node_type_arg)

        service_proposals = []
        for node in nodes:
            service_proposals += node.get_service_proposals()

        return jsonify({'proposals': service_proposals})
