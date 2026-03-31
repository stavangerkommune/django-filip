from .api import APIClient
from .exceptions import WrongConnectionTypeError
from .mssql import MSSQLClient
from .sftp import SFTPClient

CLIENT_MAP = {
    'api': APIClient,
    'sftp': SFTPClient,
    'mssql': MSSQLClient,
}


def get_client(connection):
    client_class = CLIENT_MAP.get(connection.type)
    if not client_class:
        raise WrongConnectionTypeError(f'No client implementation for type: {connection.type}')

    return client_class(connection)
