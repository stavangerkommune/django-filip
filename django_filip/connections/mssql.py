import logging
from contextlib import contextmanager
from typing import Any, cast

import pymssql

from django_filip.models import Connection

from .base import BaseConnectionClient
from .exceptions import AuthenticationError, ConnectionInactiveError

logger = logging.getLogger(__name__)


class MSSQLClient(BaseConnectionClient):
    """
    Dedicated client for connecting to Microsoft SQL Server using pymssql.

    The caller does not need to know about the driver; all connection details
    are managed internally based on the Connection model.
    """

    def __init__(self, connection: Connection):
        super().__init__(connection)
        self._check_type('mssql')

        if not connection.is_active:
            raise ConnectionInactiveError(f"Connection '{connection.name}' is inactive")

    @contextmanager
    def get_connection(self, **connect_kwargs):
        """
        Context manager to open an MSSQL connection using pymssql.

        Args:
            **connect_kwargs: Additional parameters (e.g. database, login_timeout)

        Yields:
            pymssql.Connection object
        """
        # Build connection parameters
        params = {
            'server': self.connection.host,
            'user': None,
            'password': None,
            'database': '',
            'port': self.connection.port or '1433',
            'timeout': self.connection.get_timeout(),
            'login_timeout': 60,
            'charset': 'UTF-8',
            'as_dict': True,
            **connect_kwargs,
        }

        # Handle authentication
        auth = self.connection.authentication
        if auth:
            creds = auth.get_credentials()
            if creds['type'] == 'basic':
                params['user'] = creds['username']
                params['password'] = creds['password']
            else:
                raise AuthenticationError(f'HTTP-style auth ({creds["type"]}) not supported')
        else:
            raise AuthenticationError('No authentication configured')

        conn = None
        try:
            logger.debug(f'Opening MSSQL connection to {params["server"]}:{params["port"]}')
            conn = pymssql.connect(**params)  # ty:ignore[invalid-argument-type]
            yield conn
        except Exception as e:
            logger.error(f'MSSQL connection failed for {self.connection.name}: {e}')
            raise
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    def execute_query(
        self,
        query: str,
        params: tuple | dict | None = None,
        fetch_all: bool = True,
        **connect_kwargs,
    ) -> list[dict[str, Any]] | dict[str, Any] | None:
        """
        Execute a query against the MSSQL database.

        Args:
            query: SQL query string
            params: Query parameters (tuple for positional, dict for named)
            fetch_all: If True, return all rows; False returns first row or None
            **connect_kwargs: Extra params for connection (e.g. database='mydb')

        Returns:
            List of dicts (rows), single dict (first row), or None
        """
        with self.get_connection(**connect_kwargs) as conn:
            cursor = conn.cursor()

            try:
                cursor.execute(query, params)

                if fetch_all:
                    results = cast(list[dict], cursor.fetchall())
                    logger.debug(f'Query executed: {len(results)} rows returned')
                    return results
                else:
                    result = cast(dict, cursor.fetchone())
                    logger.debug('Query executed: single row fetched')
                    return result
            except pymssql.ColumnsWithoutNamesError:
                # Handle edge case when as_dict=True but query has unnamed columns (e.g., COUNT(*))
                logger.warning('Query has unnamed columns; falling back to tuple results')
                if fetch_all:
                    return [
                        dict(zip([col[0] for col in cursor.description], row)) for row in cast(list[dict], cursor.fetchall())
                    ]
                else:
                    row = cursor.fetchone()
                    return dict(zip([col[0] for col in cursor.description], row)) if row else None
            except Exception as e:
                logger.error(f'Query failed: {query[:100]}... - {e}')
                raise
