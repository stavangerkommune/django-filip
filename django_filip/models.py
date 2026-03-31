import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, cast

import requests
from django.db import models
from django.utils import timezone
from encrypted_fields import EncryptedCharField, EncryptedTextField
from requests.auth import AuthBase

logger = logging.getLogger(__name__)


class ClientIdentity(models.Model):
    """
    Represents a client private key + optional certificate chain.
    Reusable across any authentication context:
      - mTLS for APIs (token endpoint or resource server)
      - SFTP (SSH private key)
      - Database client certificate authentication (e.g., PostgreSQL)
    """

    name = models.CharField(
        max_length=100,
        help_text="Descriptive name, e.g. 'Bank API mTLS Cert 2026', 'SFTP Jump Host Key', 'Prod DB Client Cert'",
    )

    key_type = models.CharField(
        max_length=20,
        choices=[
            ('rsa', 'RSA'),
            ('ecdsa', 'ECDSA'),
            ('ed25519', 'Ed25519'),
            ('dsa', 'DSA'),  # discouraged but supported
            ('certificate', 'X.509 Certificate + Private Key'),  # for mTLS
        ],
        help_text='Type of key. Helps with validation and usage hints.',
    )

    private_key = EncryptedTextField(
        help_text='PEM-formatted private key (with -----BEGIN ...----- headers). May be encrypted.'
    )

    passphrase = EncryptedCharField(
        max_length=255,
        blank=True,
        null=True,
        help_text='Passphrase if the private key is encrypted',
    )

    certificate_chain = EncryptedTextField(
        blank=True,
        null=True,
        help_text='Full PEM chain: client cert + intermediates (for mTLS). Optional for SSH.',
    )

    # Optional: for server certificate pinning (defense in depth)
    expected_server_fingerprint = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text='SHA256 fingerprint of expected server cert (e.g. SHA256:abc...def). '
        'Used to prevent MITM even when verify_ssl=True.',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Client Identities'

    def __str__(self):
        return '{self.name}'


class FlowType(Enum):
    NO_FLOW = 'no_flow'
    CLIENT_CREDENTIALS = 'client_credentials'


class TokenFlow(models.Model):
    flow_type = models.CharField(
        max_length=40,
        choices=[(e.value, e.name.replace('_', ' ').title()) for e in FlowType],
        default=FlowType.NO_FLOW.value,
    )
    name = models.CharField(max_length=255)

    # ── Client Credentials fields ────────────────────────────────
    client_id = models.CharField(max_length=255, blank=True)
    client_secret = EncryptedCharField(max_length=255, blank=True, null=True)
    token_url = models.URLField(blank=True, null=True)
    scope = models.CharField(max_length=1000, blank=True)

    access_token_field = models.CharField(
        max_length=100,
        default='access_token',
        help_text='JSON field name for the access token (default: access_token)',
        blank=True,
    )
    expires_in_field = models.CharField(
        max_length=100,
        default='expires_in',
        help_text="JSON field name for expires_in seconds (default: expires_in). Use '' to disable expiration.",
        blank=True,
    )

    client_identity = models.ForeignKey(
        ClientIdentity,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text='Client key/cert used when contacting token endpoint (e.g. mTLS for OAuth)',
    )

    # Optional: store last successfully obtained token
    cached_token = EncryptedCharField(max_length=2000, null=True, blank=True)
    cached_token_expires = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name_plural = 'Authentication Flows'

    def __str__(self):
        return f'{self.get_flow_type_display()} - {self.name}'  # type: ignore (django dynamic label)

    def can_obtain_token(self):
        return self.flow_type != FlowType.NO_FLOW.value

    def fetch_token(self):
        if self.flow_type == FlowType.CLIENT_CREDENTIALS.value:
            logger.info('Fetching new token.')
            now = timezone.now()
            data = {
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'scope': self.scope,
            }
            headers = {'Content-Type': 'application/x-www-form-urlencoded'}

            response = None

            try:
                response = requests.post(self.token_url, data=data, headers=headers, timeout=30)
                response.raise_for_status()
                token_data = response.json()

                access_token_field: str = cast(str, self.access_token_field) or 'access_token'
                expires_in_field: str = cast(str, self.expires_in_field).strip() or 'expires_in'

                try:
                    token = token_data[access_token_field]
                except KeyError:
                    raise ValueError(f"Missing token field '{access_token_field}' in response")

                if expires_in_field:
                    try:
                        expires_in = int(token_data[expires_in_field])
                        expires_at = now + timedelta(seconds=expires_in)
                    except (KeyError, TypeError, ValueError):
                        logger.warning(f"Could not parse '{expires_in_field}' → treating token as non-expiring")
                        expires_at = None
                else:
                    expires_at = None

                data = {
                    'bearer_token': token,
                    'bearer_expires_at': expires_at,
                }
                return data

            except requests.RequestException as e:
                logger.error(f'Token refresh failed: {e}')
                raise ValueError(f'Failed to refresh token: {e}')
            except ValueError as e:
                if response is not None:
                    logger.error(f'Token parsing failed: {e} - raw response: {response.text}')
                else:
                    # Request failed before a response was received.
                    logger.error(f'Token parsing failed: {e} - no response received.')
                raise


class AuthType(Enum):
    API_KEY = 'api_key'
    BASIC = 'basic'
    BEARER_TOKEN = 'bearer_token'
    SSH_KEY = 'ssh_key'
    # IAM_TOKEN = 'iam_token'  # Senere mulighet for AWS RDS/S3


class Authentication(models.Model):
    """
    Unified authentication configuration for connections.
    Uses type to determine which fields are relevant.
    """

    auth_type = models.CharField(
        max_length=50,
        choices=[(tag.value, tag.name.replace('_', ' ').title()) for tag in AuthType],
        db_index=True,
    )
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Auth flow - relevant for Bearer token.
    token_flow = models.ForeignKey(
        TokenFlow,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text='Optional token obtaining flow (most commonly Client Credentials)',
    )

    # API_KEY fields
    api_key_value = EncryptedCharField(max_length=500, blank=True, null=True)
    api_key_header = models.CharField(max_length=100, default='X-API-Key', blank=True)

    # BASIC fields
    basic_username = models.CharField(max_length=255, blank=True, default='')
    basic_password = EncryptedCharField(max_length=255, blank=True, null=True)

    # BEARER_TOKEN fields
    bearer_token = EncryptedCharField(max_length=2000, blank=True, null=True)
    bearer_expires_at = models.DateTimeField(blank=True, null=True)

    client_identity = models.ForeignKey(
        ClientIdentity,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text='Client key/cert used for actual API calls, SFTP session, or DB connection',
    )

    # Global override for server verification
    verify_server_cert = models.BooleanField(
        default=True,
        help_text='If False, disables server certificate validation (dangerous — use only temporarily)',
    )

    def __str__(self) -> str:
        return f'{self.get_auth_type_display()} - {self.name}'  # type: ignore (django dynamic label)

    def get_credentials(self):
        """
        Returns a dict of credentials based on type.
        Call this in connection methods for unified access.
        """
        if not self.is_active:
            raise ValueError('Auth is inactive.')

        if self.auth_type == AuthType.API_KEY.value:
            return {
                'type': 'api_key',
                'key': self.api_key_value,
                'header': self.api_key_header,
            }
        elif self.auth_type == AuthType.BASIC.value:
            return {
                'type': 'basic',
                'username': self.basic_username,
                'password': self.basic_password,
            }
        elif self.auth_type == AuthType.BEARER_TOKEN.value:
            return {
                'type': 'bearer',
                'token': self.bearer_token,
                'expires_at': self.bearer_expires_at,
            }

        raise ValueError(f'Unsupported auth type: {self.auth_type}')

    def needs_token_refresh(self, buffer_sec: int = 60) -> bool:
        if self.auth_type != AuthType.BEARER_TOKEN.value:
            return False
        if not self.bearer_token or not self.bearer_expires_at:
            return True

        now: datetime = timezone.now()
        time_for_refresh: datetime = cast(datetime, self.bearer_expires_at) - timedelta(seconds=buffer_sec)

        if now > time_for_refresh:
            logger.info(f'Time to refresh bearer token {self}...')
            return True
        else:
            return False

    def fetch_and_save_token(self) -> str:
        token_data: dict[str, Any] | None = cast(TokenFlow, self.token_flow).fetch_token()
        if token_data is not None:
            self.bearer_token = token_data['bearer_token']
            self.bearer_expires_at = token_data['bearer_expires_at']
            self.save()
        return cast(str, self.bearer_token) or ''

    def get_current_token(self) -> str:
        """Get a valid bearer token, refresh if necessary."""
        if self.auth_type != AuthType.BEARER_TOKEN.value:
            raise ValueError('get_current_token only supports bearer auth')

        if self.needs_token_refresh():
            fresh_token = self.fetch_and_save_token()
            return fresh_token

        return cast(str, self.bearer_token) or ''

    def get_bearer_auth_handler(self):
        """
        Returns a requests-compatible AuthBase instance that automatically
        refreshes the bearer token when needed.
        """
        if self.auth_type != AuthType.BEARER_TOKEN.value:
            raise ValueError('get_bearer_auth_handler only valid for bearer token auth.')

        class DynamicBearerAuth(AuthBase):
            def __init__(self_inner):
                self_inner.auth_model = self
                self_inner._last_known_token = None

            def _ensure_valid_token(self_inner):
                # Caching layer
                current = self_inner.auth_model.bearer_token
                if (
                    self_inner._last_known_token is None
                    or self_inner._last_known_token != current
                    or self_inner.auth_model.needs_token_refresh()
                ):
                    self_inner._last_known_token = self_inner.auth_model.get_current_token()

            def __call__(self_inner, request):
                self_inner._ensure_valid_token()
                request.headers['Authorization'] = f'Bearer {self_inner._last_known_token}'
                return request

        return DynamicBearerAuth()


class ConnectionType(Enum):
    API = 'api'
    SFTP = 'sftp'
    MSSQL = 'mssql'


class Connection(models.Model):
    """
    Represents a reusable connection to an external system.
    """

    type = models.CharField(
        max_length=50,
        choices=[(tag.value, tag.name.replace('_', ' ').title()) for tag in ConnectionType],
    )
    name = models.CharField(max_length=255)
    authentication = models.ForeignKey(Authentication, on_delete=models.PROTECT, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    host = models.CharField(max_length=255)
    port = models.IntegerField(
        null=True,
        blank=True,
        help_text='e.g., 80/443 for API, 22 for SFTP, 1433 for MSSQL, 5432 for PostgreSQL, 8080 for internal API etc.',
    )

    timeout_seconds = models.PositiveIntegerField(null=True, blank=True)

    expected_sftp_host_key_fingerprint = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text='For SFTP/SSH: expected SHA256 host key fingerprint (e.g. SHA256:xxx). Enforces known host verification.',
    )

    _client_cache = None

    class Meta:
        unique_together = ['type', 'name']
        ordering = ['type', 'name']
        verbose_name = 'Connection'
        verbose_name_plural = 'Connections'

    @property
    def client(self):
        """Returns the appropriate specialized client for this connection type"""
        # TODO: use shared cache / redis for multi-container environments
        if self._client_cache is None:
            from .connections import get_client

            self._client_cache = get_client(self)

        return self._client_cache

    def get_timeout(self):
        """
        Returns the timeout value in seconds to use for operations on this connection.

        Uses the explicit timeout_seconds if set, otherwise returns a reasonable default.
        """
        if self.timeout_seconds is not None:
            return self.timeout_seconds

        type_defaults = {
            'api': 30,
            'sftp': 120,
            'database': 60,
        }

        return type_defaults.get(cast(str, self.type), 30)  # fallback to 30s for unknown/safe default

    def __str__(self):
        return f'{self.get_type_display()} — {self.name} ({self.host}{f":{self.port}" if self.port else ""})'  # type: ignore (django dynamic label)
