# Security Policy

## Supported versions

Security fixes are applied to the latest release and the default branch. Until the first release is published, only the default branch is supported.

## Reporting a vulnerability

Do not open a public issue for a vulnerability. Use GitHub's private vulnerability reporting for this repository. Include the affected revision, deployment mode, threat scenario, reproduction steps, and whether credentials or physical cooling may be affected.

Please remove real IP addresses, passwords, private keys, host keys, hardware serial numbers, and other identifying data from reports and logs.

## Security boundaries

The controller can run as root, execute administrator-configured sensor commands, connect over SSH, handle IPMI and SSH credentials, and issue raw IPMI commands that change physical fan behavior. Changes involving these boundaries require tests and explicit maintainer review.

The monitoring Web service is read-only and binds to `127.0.0.1` by default. It is not an authentication or authorization boundary and must not be exposed directly to an untrusted network.
