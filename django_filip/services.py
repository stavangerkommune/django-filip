import logging
import os
import socket
from pathlib import Path
from typing import Literal, cast

import paramiko
import pymssql

# Set up logger
logger = logging.getLogger(__name__)


def upload_sftp(
    server: str,
    username: str,
    password: str | None = None,
    key_path: str | None = None,
    file: str | None = None,
    port: int = 22,
    remote_path: str | None = None,
    remote_filename: str | None = None,
    overwrite: bool = True,
    timeout: int = 10,
) -> str | None:
    """
    Upload a file to an SFTP server.

    Args:
        server: SFTP server hostname or IP
        username: SFTP username
        password: Password for authentication (mutually exclusive with key_path)
        key_path: Path to private key file (mutually exclusive with password)
        file: Local path of file to upload
        port: SFTP port
        remote_path: Remote directory (None = home directory)
        remote_filename: Remote filename (None = use local filename)
        overwrite: Whether to overwrite an existing file
        timeout: Connection timeout in seconds

    Returns:
        Full remote path of uploaded file, or None if upload failed or was skipped
    """

    if file is None:
        raise ValueError('file cannot be None')
    if not os.path.isfile(file):
        raise ValueError(f'{file} is not a valid file')
    if password is None and key_path is None:
        raise ValueError('Must provide either password or key_path')

    local_file = Path(file)
    remote_filename = remote_filename or local_file.name

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        if key_path:
            private_key = paramiko.RSAKey.from_private_key_file(key_path)
            ssh.connect(server, port=port, username=username, pkey=private_key, timeout=timeout)
        else:
            ssh.connect(server, port=port, username=username, password=password, timeout=timeout)

        with ssh.open_sftp() as sftp:
            _ch_or_mkdir(sftp, remote_path)
            cwd = sftp.getcwd() or '/'

            if not overwrite:
                try:
                    sftp.stat(remote_filename)
                    return None
                except IOError:
                    pass

            sftp.put(local_file, remote_filename)
            return f'{cwd.rstrip("/")}/{remote_filename}'.lstrip('/')

    except (paramiko.SSHException, socket.timeout) as e:
        # Log the error with Django logger
        logger.error(f'SFTP connection/upload failed for {file}: {e}')
        return None
    finally:
        ssh.close()


def _ch_or_mkdir(sftp, remote_path):
    if remote_path is None:
        sftp.chdir(None)
        return

    # Handle Path object or string
    path = Path(remote_path) if not isinstance(remote_path, Path) else remote_path

    # Empty path or root
    if not path.parts or path == Path('/'):
        sftp.chdir('/')
        return

    current_path = ''
    for part in path.parts:
        if part:  # Skip empty parts
            current_path = f'{current_path}/{part}'.lstrip('/')
            try:
                sftp.stat(current_path)
            except IOError:
                sftp.mkdir(current_path)

    sftp.chdir(current_path)  # Convert to string only when needed for SFTP


def db_fetch(
    dbtype: Literal['mssql', 'postgresql'],
    server: str,
    user: str,
    password: str,
    query: str,
    one_line: bool = False,
) -> list[dict] | dict | None:
    """
    Run SQL query against MSSQL or PostgreSQL.

    When `one_line=True` returns the first row as a dict (or None if no rows).

    Returns:
        - When one_line=False: list[dict] of rows, or None if no rows
        - When one_line=True:  dict (first row), or None if no rows

    Raises:
        ValueError: bad dbtype
        dbapi exceptions on connection/query errors
    """

    if dbtype == 'mssql':
        with pymssql.connect(server, user, password) as conn:
            with conn.cursor(as_dict=True) as cursor:
                cursor.execute(query)

                # Are we expecting only 1 line, or do we want everything?
                if one_line:
                    output = cast(dict, cursor.fetchone())
                else:
                    output = cast(list[dict], cursor.fetchall())

        return output

    elif dbtype == 'postgresql':
        # TODO: write this one out
        pass
    else:
        pass
