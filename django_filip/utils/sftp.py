import logging
import os
import socket
from pathlib import Path

import paramiko

# Set up logger
logger = logging.getLogger(__name__)


def upload_sftp(
    server,
    username,
    password=None,
    key_path=None,
    file=None,
    port=22,
    remote_path=None,
    remote_filename=None,
    overwrite=True,
    timeout=10,
):
    """
    Upload a file to an SFTP server.

    Args:
        server (str): SFTP server hostname or IP.
        username (str): SFTP username.
        password (str, optional): Password for authentication (if no key).
        key_path (str, optional): Path to private key file for authentication.
        file (str): Local path to the file to upload.
        port (int): SFTP port (default: 22).
        remote_path (str, optional): Remote directory to upload to (None = home dir).
        remote_filename (str, optional): Remote filename (defaults to local filename).
        overwrite (bool, optional): Overwrite remote file if it exists (default: True).
        timeout (int, optional): Connection timeout in seconds (default: 10).

    Returns:
        str: Full remote path of the uploaded file, or None if skipped or failed.
    """
    if file is None:
        raise ValueError("file cannot be None")
    if not os.path.isfile(file):
        raise ValueError(f"{file} is not a valid file")
    if password is None and key_path is None:
        raise ValueError("Must provide either password or key_path")

    local_file = Path(file)
    remote_filename = remote_filename or local_file.name

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        if key_path:
            private_key = paramiko.RSAKey.from_private_key_file(key_path)
            ssh.connect(
                server, port=port, username=username, pkey=private_key, timeout=timeout
            )
        else:
            ssh.connect(
                server, port=port, username=username, password=password, timeout=timeout
            )

        with ssh.open_sftp() as sftp:
            _ch_or_mkdir(sftp, remote_path)
            cwd = sftp.getcwd() or "/"

            if not overwrite:
                try:
                    sftp.stat(remote_filename)
                    return None
                except IOError:
                    pass

            sftp.put(local_file, remote_filename)
            return f"{cwd.rstrip('/')}/{remote_filename}".lstrip("/")

    except (paramiko.SSHException, socket.timeout) as e:
        # Log the error with Django logger
        logger.error(f"SFTP connection/upload failed for {file}: {e}")
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
    if not path.parts or path == Path("/"):
        sftp.chdir("/")
        return

    current_path = ""
    for part in path.parts:
        if part:  # Skip empty parts
            current_path = f"{current_path}/{part}".lstrip("/")
            try:
                sftp.stat(current_path)
            except IOError:
                sftp.mkdir(current_path)

    sftp.chdir(current_path)  # Convert to string only when needed for SFTP
