import logging
from io import BytesIO
from pathlib import Path
from typing import BinaryIO

import paramiko
from paramiko import ECDSAKey, Ed25519Key, RSAKey

from django_filip.models import Authentication, Connection

from .base import BaseConnectionClient
from .exceptions import AuthenticationError, ConnectionInactiveError

logger = logging.getLogger(__name__)


class SFTPClient(BaseConnectionClient):
    """
    Client for SFTP connections.
    Provides file upload/download and directory listing.

    Uses paramiko under the hood and integrates with Connection model
    for authentication, host key verification, and timeout.
    """

    _transport: paramiko.Transport | None = None
    _sftp: paramiko.SFTPClient | None = None

    def __init__(self, connection: Connection):
        super().__init__(connection)
        self._check_type('sftp')

        if not connection.is_active:
            raise ConnectionInactiveError(f"Connection '{connection.name}' is inactive.")

        self._connect_if_needed()

    def _connect_if_needed(self):
        """
        Lazily establish SFTP connection when first operation is called
        """
        if self._sftp is not None:
            # Already connected
            return

        port = self.connection.port or 22
        timeout = self.connection.get_timeout()

        try:
            self._transport = paramiko.Transport((self.connection.host, port))
            self._transport.set_keepalive(timeout)

            # Strict host key verification if fingerprint is provided
            if self.connection.expected_sftp_host_key_fingerprint:
                self._verify_host_key()

            # Authentication
            auth = self.connection.authentication
            if not auth:
                raise AuthenticationError('No authentication configures for SFTP connection')

            if auth.client_identity:
                # SSH private key from ClientIdentity
                identity = auth.client_identity
                pkey = self._load_private_key(identity)
                self._transport.connect(username=self._get_username(auth), pkey=pkey)
            else:
                # Fallback to password
                creds = auth.get_credentials()
                if creds['type'] == 'basic':
                    self._transport.connect(username=creds['username'], password=creds['password'])
                else:
                    raise AuthenticationError(
                        f'Unsupported auth type for SFTP: {creds["type"]}.Use ClientIdentity with SSH private key'
                    )

            self._sftp = paramiko.SFTPClient.from_transport(self._transport)
            logger.info(f'SFTP connection established to {self.connection.host}:{port}')

        except Exception as e:
            logger.error(f'SFTP connection failed for {self.connection.name}: {e}')
            raise

    def _verify_host_key(self):
        """Verify server host key against expected fingerprint."""
        expected = self.connection.expected_sftp_host_key_fingerprint.strip()
        if not expected.startswith('SHA256:'):
            expected = f'SHA256:{expected}'

        # Get remote host key
        remote_key = self._transport.remote_server_key  # type: ignore
        if not remote_key:
            raise AuthenticationError('could not obtain remote host key')

        # Compute SHA256 fingerprint
        fingerprint = remote_key.get_fingerprint().hex()
        computed = 'SHA256:' + fingerprint

        if computed != expected:
            raise AuthenticationError(
                f'Host key verification failed for {self.connection.host}-Expected: {expected} , got: {computed}'
            )

        logger.debug('Host key fingerprint verified successfully')

    def _load_private_key(self, identity):
        """Load private key from ClientIdentity (supports passphrase)."""
        key_data = identity.private_key
        passphrase = identity.passphrase

        # Try different key types
        for key_class in [RSAKey, Ed25519Key, ECDSAKey]:
            try:
                from io import StringIO

                key_file = StringIO(key_data)
                return key_class.from_private_key(key_file, password=passphrase.encode() if passphrase else None)
            except Exception:
                continue

        raise AuthenticationError('Failed to load private key from ClientIdentity')

    def _get_username(self, auth: Authentication) -> str:
        """Extract username for SFTP-"""
        creds = auth.get_credentials()
        if creds['type'] == 'basic':
            return creds['username']

        raise AuthenticationError('No username available for SFTP authentication')

    # Public API

    def upload(
        self, file_object: BinaryIO | bytes, remote_directory: str, remote_filename: str, overwrite: bool = True
    ) -> str:
        """
        Upload a local file to the remote server.

        Returns full remote path of uploaded file
        """
        self._connect_if_needed()

        self._mkdir_p(remote_directory)
        self._sftp.chdir(remote_directory)  # type: ignore

        if not overwrite:
            try:
                self._sftp.stat(remote_filename)  # type: ignore
                logger.info(f'File exists, skipping upload: {remote_filename}')
                return f'{remote_directory}/{remote_filename}'
            except FileNotFoundError:
                pass

        remote_full_path = f'{remote_directory}/{remote_filename}'

        # Check if the input is raw bytes data:
        if isinstance(file_object, bytes):
            with self._sftp.open(remote_full_path, 'wb') as remote_file:  # type: ignore
                # write entire byes object in one operation, since it is already in memory
                remote_file.write(file_object)

        # If file_object is a file-like object (like Django FileField, BytesIO etc.)
        else:
            with self._sftp.open(remote_full_path, 'wb') as remote_file:  # type: ignore
                # Read data in 8KB chunks to avoid loading large files entirely into memory
                while chunk := file_object.read(8192):
                    remote_file.write(chunk)

        logger.info(f'Uploaded {remote_filename} to {remote_directory}')
        return remote_full_path

    def download_to_disk(self, remote_path: str, local_path: str) -> Path:
        """Download a remote file to disk"""
        self._connect_if_needed()

        local_file = Path(local_path)
        local_file.parent.mkdir(parents=True, exist_ok=True)

        self._sftp.get(remote_path, str(local_file))  # type: ignore
        logger.info(f'Downloaded {remote_path} --> {local_path}')
        return local_file

    def download_to_memory(self, remote_path: str) -> BytesIO:
        """Download file to memory"""
        buffer = BytesIO()
        with self._sftp.open(remote_path, 'rb') as remote_file:  # type: ignore
            while chunk := remote_file.read(8192):
                buffer.write(chunk)

        buffer.seek(0)
        logger.info(f'Downloaded {remote_path} to memory')
        return buffer

    def list_dir(self, path: str = '.') -> list[str]:
        """List files in the specified remote directory."""
        self._connect_if_needed()
        return self._sftp.listdir(path)  # type: ignore

    def _mkdir_p(self, remote_path: str):
        """Recursive mkdir like os.makedirs"""
        if not remote_path:
            return

        parts = Path(remote_path).parts
        current = ''
        for part in parts:
            if part:
                current = f'{current}/{part}'.lstrip('/')
                try:
                    self._sftp.stat(current)  # type: ignore
                except FileNotFoundError:
                    self._sftp.mkdir(current)  # type: ignore

    def close(self):
        """Close SFTP and transport connection."""
        if self._sftp:
            try:
                self._sftp.close()
            except Exception:
                pass

        self._sftp = None
        self._transport = None
        logger.debug(f'SFTP connection closed for {self.connection.name}.')

    def __del__(self):
        """Auto-close on object destruction"""
        self.close()
