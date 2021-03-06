import json
from datetime import datetime, timedelta

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Index, ForeignKey, ForeignKeyConstraint
from sqlalchemy.orm import relationship

db = SQLAlchemy()

EMAIL_LENGTH_LIMIT = 254
REFERRAL_CODE_LIMIT = 64
IDENTITY_LENGTH_LIMIT = 42
SESSION_KEY_LIMIT = 36
AVAILABILITY_TIMEOUT = timedelta(minutes=6)
SESSION_EXPIRATION = timedelta(minutes=10)


# TODO: rename to Proposal, since single Node can have multiple proposals
class Node(db.Model):
    __tablename__ = 'node'
    node_key = db.Column(db.String(IDENTITY_LENGTH_LIMIT), primary_key=True)
    ip = db.Column(db.String(45))
    connection_config = db.Column(db.Text)

    proposal = db.Column(db.Text)
    service_type = db.Column(db.String(255), primary_key=True)

    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime, index=True)

    monitoring_failed = relationship("MonitoringFailed")
    access_policies = relationship("ProposalAccessPolicy")

    node_type = db.Column(
        db.String(255),
        default="data-center",
        nullable=False
    )

    def __init__(self, node_key, service_type):
        self.node_key = node_key
        self.service_type = service_type
        self.created_at = datetime.utcnow()

    def is_active(self):
        return _is_active(self.updated_at)

    def status(self):
        return 'Online' if self.is_active() else 'Offline'

    def mark_activity(self):
        self.updated_at = datetime.utcnow()

    def mark_inactive(self):
        # TODO this is bad, need a good way to save unregistered node state
        # time in percona is rounded to seconds,
        # so need additional 1 second to ensure node becomes inactive instantly
        value = datetime.utcnow() - AVAILABILITY_TIMEOUT - timedelta(seconds=1)
        self.updated_at = value

    def get_service_proposals(self):
        try:
            proposal = json.loads(self.proposal)
        except ValueError:
            return []
        return [proposal]

    def get_country_from_service_proposal(self):
        proposals = self.get_service_proposals()

        try:
            service_definition = proposals[0]['service_definition']
            return service_definition['location_originate']['country']
        except KeyError:
            pass

        try:
            service_definition = proposals[0]['service_definition']
            return service_definition['location']['country']
        except KeyError:
            return None


class ProposalAccessPolicy(db.Model):
    __tablename__ = 'proposal_access_policy'
    node_key = db.Column(db.String(IDENTITY_LENGTH_LIMIT),
                         ForeignKey('node.node_key'), primary_key=True)
    id = db.Column(db.String(255), primary_key=True)
    source = db.Column(db.String(255), primary_key=True)

    def __init__(self, node_key: str, id: str, source: str):
        self.node_key = node_key
        self.id = id
        self.source = source


class Session(db.Model):
    __tablename__ = 'session'

    session_key = db.Column(db.String(SESSION_KEY_LIMIT), primary_key=True)
    # TODO: rename to provider_id
    node_key = db.Column(db.String(IDENTITY_LENGTH_LIMIT), index=True)
    created_at = db.Column(db.DateTime)
    node_updated_at = db.Column(db.DateTime)
    client_updated_at = db.Column(db.DateTime, index=True)
    node_bytes_sent = db.Column(db.BigInteger)
    node_bytes_received = db.Column(db.BigInteger)
    consumer_id = db.Column(db.String(IDENTITY_LENGTH_LIMIT))
    client_bytes_sent = db.Column(db.BigInteger)
    client_bytes_received = db.Column(db.BigInteger)
    client_ip = db.Column(db.String(45))
    client_country = db.Column(db.String(255))
    established = db.Column(db.Boolean)
    service_type = db.Column(db.String(255), nullable=False)

    def __init__(self, session_key, service_type):
        self.session_key = session_key
        self.service_type = service_type
        self.created_at = datetime.utcnow()
        self.established = False
        self.node_bytes_sent = 0
        self.node_bytes_received = 0
        self.client_bytes_sent = 0
        self.client_bytes_received = 0

    def is_active(self):
        return _is_active(self.client_updated_at)

    def has_expired(self):
        last_session_activity = self.client_updated_at or self.created_at
        return datetime.utcnow() - last_session_activity > SESSION_EXPIRATION


class NodeAvailability(db.Model):
    __tablename__ = 'node_availability'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    node_key = db.Column(db.String(IDENTITY_LENGTH_LIMIT))
    date = db.Column(db.DateTime)
    service_type = db.Column(db.String(255), nullable=False)

    def __init__(self, node_key):
        self.node_key = node_key
        self.date = datetime.utcnow()


Index(
    'node_availability_fast_stats_index',
    NodeAvailability.node_key, NodeAvailability.date
)


class Identity(db.Model):
    __tablename__ = 'identity'
    identity = db.Column(db.String(IDENTITY_LENGTH_LIMIT), primary_key=True)
    created_at = db.Column(db.DateTime)

    def __init__(self, identity):
        self.identity = identity
        self.created_at = datetime.utcnow()


def _is_active(last_update_time):
    if last_update_time is None:
        return False
    passed = datetime.utcnow() - last_update_time
    return passed < AVAILABILITY_TIMEOUT


class IdentityRegistration(db.Model):
    __tablename__ = 'identity_registration'
    identity = db.Column(db.String(IDENTITY_LENGTH_LIMIT), primary_key=True)
    email = db.Column(db.String(EMAIL_LENGTH_LIMIT))
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime)
    payout_eth_address = db.Column(db.String(IDENTITY_LENGTH_LIMIT))
    referral_code = db.Column(db.String(REFERRAL_CODE_LIMIT))
    bounty_program = db.Column(db.Boolean, default=False, nullable=False)

    def __init__(self, identity, payout_eth_address,
                 referral_code='', email=''):
        self.identity = identity
        self.created_at = datetime.utcnow()
        self.payout_eth_address = payout_eth_address
        self.email = email
        self.referral_code = referral_code

    def update(self, payout_eth_address):
        self.updated_at = datetime.utcnow()
        self.payout_eth_address = payout_eth_address

    def update_email(self, email):
        self.updated_at = datetime.utcnow()
        self.email = email

    def update_referral_code(self, referral_code=""):
        self.updated_at = datetime.utcnow()
        if bool(referral_code and referral_code.strip()):
            if not bool(self.referral_code and self.referral_code.strip()):
                self.referral_code = referral_code


class Affiliate(db.Model):
    __tablename__ = 'affiliates'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(EMAIL_LENGTH_LIMIT))
    payout_eth_address = db.Column(db.String(IDENTITY_LENGTH_LIMIT))
    referral_code = db.Column(db.String(REFERRAL_CODE_LIMIT))
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime)

    def __init__(self, email, payout_eth_address, referral_code):
        self.email = email
        self.created_at = datetime.utcnow()
        self.payout_eth_address = payout_eth_address
        self.referral_code = referral_code

    def update(self, referral_code):
        self.updated_at = datetime.utcnow()
        self.referral_code = referral_code


class PaymentTokens(db.Model):
    __tablename__ = 'payments_tokens'
    provider_id = db.Column(db.String(IDENTITY_LENGTH_LIMIT), primary_key=True)
    updated_at = db.Column(db.DateTime)
    tokens = db.Column(db.BigInteger)

    def __init__(self, provider_id, tokens):
        self.provider_id = provider_id
        self.updated_at = datetime.utcnow()
        self.tokens = tokens

    def update(self, tokens):
        self.updated_at = datetime.utcnow()
        self.tokens = tokens


class MonitoringFailed(db.Model):
    __tablename__ = 'monitoring_failed'
    provider_id = db.Column(db.String(IDENTITY_LENGTH_LIMIT), primary_key=True)
    service_type = db.Column(db.String(255), primary_key=True)
    __table_args__ = (ForeignKeyConstraint(['provider_id', 'service_type'], ['node.node_key', 'node.service_type']), {})

    def __init__(self, provider_id, service_type):
        self.provider_id = provider_id
        self.service_type = service_type
