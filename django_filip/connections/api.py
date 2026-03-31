from requests_ratelimiter import LimiterSession, MemoryQueueBucket

from ..helpers import build_url
from .base import BaseConnectionClient


class APIClient(BaseConnectionClient):
    """Client for HTTP/API connections"""

    def __init__(self, connection):
        super().__init__(connection)
        self._check_type('api')

        self.base_url = self._build_base_url()
        self.session = self._create_session()

    def _build_base_url(self):
        return self.connection.host

    def _create_session(self):
        session = LimiterSession(
            per_minute=300,  # TODO: read from connection.rate_limit_calls
            bucket_class=MemoryQueueBucket,
        )

        # Apply authentication, certificates
        authentication = self.connection.authentication
        if authentication:
            creds = authentication.get_credentials()
            if creds['type'] == 'api_key':
                session.headers[creds['header']] = creds['key']
            elif creds['type'] == 'bearer':
                session.auth = authentication.get_bearer_auth_handler()

            # mTLS client cert
            if authentication.client_identity:
                iden = authentication.client_identity
                cert = (iden.certificate_chain, iden.private_key) if iden.certificate_chain else iden.private_key
                session.cert = cert

            session.verify = authentication.verify_server_cert if authentication else True

        return session

    # Public API
    def get(self, path='', params=None, **kwargs):
        """
        Perform an HTTP GET request.

        Args:
            path: API endpoint path (will be appended to base_url)
            params: Query parameters (dict)
            **kwargs: Additional requests kwargs (headers, timeout override, etc.)
        """
        url = build_url(self.base_url, path)

        return self.session.get(url, params=params, timeout=self.get_timeout(), **kwargs)

    def post(self, path='', json=None, data=None, **kwargs):
        """
        Perform an HTTP POST request.

        Args:
            path: API endpoint path
            json: JSON payload (preferred)
            data: Form-encoded data (alternative)
            **kwargs: Additional requests kwargs
        """
        url = build_url(self.base_url, path)
        return self.session.post(url, json=json, data=data, timeout=self.get_timeout(), **kwargs)

    def put(self, json=None, data=None, path='', **kwargs):
        """
        Perform an HTTP PUT request (usually for full resource replacement).

        Args:
            path: API endpoint path
            json: JSON payload
            data: Form-encoded data (alternative)
            **kwargs: Additional requests kwargs
        """
        url = build_url(self.base_url, path)
        return self.session.put(url, json=json, data=data, timeout=self.get_timeout(), **kwargs)

    def patch(self, path='', json=None, data=None, **kwargs):
        """
        Perform an HTTP PATCH request (usually for partial resource updates).

        Args:
            path: API endpoint path
            json: JSON payload (partial update)
            data: Form-encoded data (alternative)
            **kwargs: Additional requests kwargs
        """
        url = build_url(self.base_url, path)
        return self.session.patch(url, json=json, data=data, timeout=self.get_timeout(), **kwargs)

    def delete(self, path='', **kwargs):
        """
        Perform an HTTP DELETE request.

        Args:
            path: API endpoint path (resource to delete)
            **kwargs: Additional requests kwargs
        """
        url = build_url(self.base_url, path)
        return self.session.delete(url, timeout=self.get_timeout(), **kwargs)

    def request(self, method, path='', **kwargs):
        """
        Generic HTTP request method for any verb.

        Args:
            method: HTTP method ('GET', 'POST', 'PUT', 'PATCH', 'DELETE', etc.)
            path: API endpoint path
            **kwargs: All other requests kwargs
        """
        url = build_url(self.base_url, path)
        return self.session.request(method.upper(), url, timeout=self.get_timeout(), **kwargs)
