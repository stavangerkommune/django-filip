from abc import ABC


class BaseConnectionClient(ABC):
    """Base clas for all protocol-specific clients"""

    def __init__(self, connection):
        self.connection = connection

        if not hasattr(connection, 'type'):
            raise ValueError('Connection object must have a "type" attribute')

    def _check_type(self, expected_type):
        if self.connection.type != expected_type:
            raise TypeError(
                f'This client is only for "{expected_type}" connections.'
                f'Got: "{self.connection.type}" ({self.connection.name})'
            )

    def get_auth(self):
        return self.connection.auth

    def get_timeout(self):
        return self.connection.timeout_seconds or 30
