import sys
import datetime
import shlex
import subprocess
from dataclasses import dataclass
from typing import Optional, Sequence, Union


@dataclass(frozen=True)
class CommandSpec:
    argv: Sequence[str]
    stdin_data: Optional[str] = None


Command = Union[str, Sequence[str], CommandSpec]
SENSITIVE_CONFIG_KEYS = {'password', 'key_path', 'private_key', 'token', 'api_key'}


def format_command(command: Command) -> str:
    if isinstance(command, CommandSpec):
        return shlex.join(command.argv)
    if isinstance(command, str):
        return command
    return shlex.join(command)


def redact_mapping(value):
    if isinstance(value, dict):
        return {
            key: '***' if str(key).lower() in SENSITIVE_CONFIG_KEYS else redact_mapping(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_mapping(item) for item in value]
    return value


def configure_ssh_client(client, paramiko_module):
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko_module.RejectPolicy())
    return client

def log(level, tag, msg, file=sys.stdout):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    level = level.upper()
    tag_str = f"[{tag}]" if tag else ""
    print(f"[{now}][{level}]{tag_str} {msg}", file=file)

def ssh_exec_command(
    host: str,
    username: str,
    command: Command,
    password: str = None,
    key_path: str = None,
    logger=log,
    log_tag: str = None,
    debug: bool = False
):
    import paramiko

    ssh = paramiko.SSHClient()
    configure_ssh_client(ssh, paramiko)
    try:
        if key_path:
            ssh.connect(host, username=username, key_filename=key_path)
        else:
            ssh.connect(host, username=username, password=password)
        if isinstance(command, CommandSpec):
            remote_command = shlex.join(command.argv)
            stdin_data = command.stdin_data
        elif isinstance(command, str):
            remote_command = command
            stdin_data = None
        else:
            remote_command = shlex.join(command)
            stdin_data = None
        stdin, stdout, stderr = ssh.exec_command(remote_command)
        if stdin_data is not None:
            stdin.write(stdin_data)
            stdin.flush()
            stdin.channel.shutdown_write()
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
    if debug:
        log("DEBUG", log_tag, f"Command for {log_tag}: {format_command(command)}")

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
            if isinstance(command, CommandSpec):
                result = subprocess.run(
                    command.argv,
                    input=command.stdin_data,
                    shell=False,
                    capture_output=True,
                    text=True,
                )
            elif isinstance(command, str):
                # Sensor pipelines are an explicit administrator-authored part
                # of the local configuration and require shell syntax.
                result = subprocess.run(command, shell=True, capture_output=True, text=True)
            else:
                result = subprocess.run(command, shell=False, capture_output=True, text=True)
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

def auto_split_thresholds(temp_min, temp_max, speed_min, speed_max, hysteresis):
    thresholds = []
    speeds = []
    n = max(1, round((float(temp_max) - float(temp_min)) / (float(hysteresis) * 2)))
    for i in range(n + 1):
        t = float(temp_min) + (float(temp_max) - float(temp_min)) * i / n
        thresholds.append(round(t, 2))
    for i in range(len(thresholds)):
        s = speed_min + (speed_max - speed_min) * (i / (len(thresholds) - 1)) if len(thresholds) > 1 else speed_max
        speeds.append(round(s))
    return thresholds, speeds
