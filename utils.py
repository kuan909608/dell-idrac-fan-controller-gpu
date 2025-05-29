import sys
import datetime
import paramiko
import subprocess

def log(level, tag, msg, file=sys.stdout):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    level = level.upper()
    tag_str = f"[{tag}]" if tag else ""
    print(f"[{now}][{level}]{tag_str} {msg}", file=file)

def ssh_exec_command(
    host: str,
    username: str,
    command: str,
    password: str = None,
    key_path: str = None,
    logger=log,
    log_tag: str = None,
    debug: bool = False
):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        if key_path:
            pkey = paramiko.RSAKey.from_private_key_file(key_path)
            ssh.connect(host, username=username, pkey=pkey)
        else:
            ssh.connect(host, username=username, password=password)
        stdin, stdout, stderr = ssh.exec_command(command)
        output = stdout.read().decode().strip()
        error = stderr.read().decode()
        if logger:
            if debug:
                logger("DEBUG", log_tag, f"SSH output: {output}")
            if error and error.strip():
                logger("ERROR", log_tag, f"SSH error: {error.strip()}")
        return output, error
    except paramiko.AuthenticationException as e:
        if logger:
            logger("ERROR", log_tag, f"SSH authentication failed: {e}")
        return None, str(e)
    except paramiko.SSHException as e:
        if logger:
            logger("ERROR", log_tag, f"SSH error: {e}")
        return None, str(e)
    except Exception as e:
        if logger:
            logger("ERROR", log_tag, f"SSH connection failed: {e}")
        return None, str(e)
    finally:
        try:
            ssh.close()
        except Exception:
            pass


def run_command(host_dict, command, logger=log, log_tag=None, debug: bool = False):
    ssh_creds = host_dict.get('ssh_credentials')
    if ssh_creds:
        return ssh_exec_command(
            host=ssh_creds.get('host'),
            username=ssh_creds.get('username'),
            password=ssh_creds.get('password'),
            key_path=ssh_creds.get('key_path'),
            command=command,
            logger=logger,
            log_tag=log_tag,
            debug=debug
        )
    else:
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            output = result.stdout.strip()
            error = result.stderr.strip()
            if logger:
                if debug:
                    logger("DEBUG", log_tag, f"Local output: {output}")
                if error:
                    logger("ERROR", log_tag, f"Local error: {error}")
            return output, error
        except Exception as e:
            if logger:
                logger("ERROR", log_tag, f"Local command failed: {e}")
            return None, str(e)
