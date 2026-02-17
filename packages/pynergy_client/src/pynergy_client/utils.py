import datetime
import hashlib
import json
import ssl
import sys
from pathlib import Path
from typing import Tuple

import questionary
import typer
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from loguru import logger

from . import config
from .device import (
    BaseDeviceContext,
    BaseKeyboardVirtualDevice,
    BaseMouseVirtualDevice,
    UInputKeyboardDevice,
    UInputMouseDevice,
    WaylandDeviceContext,
)
from .device.base import PlatformInfo


def init_logger(cfg: config.Config):
    """
    Initialize logger.

    This function removes default handlers and adds two new handlers:
    1. Stdout handler: Displays logs in real-time with colors and concise format.
    2. File handler: Records logs to specified file with size-based rotation and compression.

    Args:
        cfg: config dict
    """
    logger.remove()
    log_path = Path(cfg.log_dir) / cfg.log_file
    logger.add(
        sys.stdout,
        level=cfg.log_level_stdout,
        format='<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>',
        colorize=True,
        diagnose=False,
    )

    logger.add(
        log_path,
        level=cfg.log_level_file,
        rotation='10 MB',
        compression='zip',
        format='{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}',
        diagnose=False,
    )

    logger.bind(name=cfg.logger_name)


def init_backend(
    cfg: config.Config,
) -> Tuple[
    BaseDeviceContext | None, BaseMouseVirtualDevice | None, BaseKeyboardVirtualDevice | None
]:
    """
    Initialize input device backend.

    This function calls the corresponding initialization function based on the
    input device backend name in the configuration.

    Args:
        cfg: config dict
    """
    device_ctx = None
    mouse = None
    keyboard = None

    platform_info = PlatformInfo()
    match platform_info.platform.lower():
        case 'linux':
            match platform_info.session_type.lower():
                case 'wayland':
                    device_ctx = WaylandDeviceContext()
                    if not cfg.mouse_backend:
                        mouse = UInputMouseDevice()
                    if not cfg.keyboard_backend:
                        keyboard = UInputKeyboardDevice()
                case _:
                    raise NotImplementedError(
                        f'Unsupported session type: {platform_info.session_type}'
                    )

            logger.info(f'Using {platform_info.session_type} backend')
        case _:
            raise NotImplementedError(f'Unsupported platform: {platform_info.platform}')

    if cfg.mouse_backend is not None:
        match cfg.mouse_backend:
            case 'uinput':
                mouse = UInputMouseDevice()
            case 'libei':
                raise NotImplementedError('libei backend is WiP')
            case 'wlr':
                raise NotImplementedError('wlr backend is WiP')
            case _:
                raise ValueError(f'Unsupported mouse backend: {cfg.mouse_backend}')

    if cfg.keyboard_backend is not None:
        match cfg.keyboard_backend:
            case 'uinput':
                keyboard = UInputKeyboardDevice()
            case 'libei':
                raise NotImplementedError('libei backend is WiP')
            case 'wlr':
                raise NotImplementedError('wlr backend is WiP')
            case _:
                raise ValueError(f'Unsupported keyboard backend: {cfg.keyboard_backend}')

    logger.info(f'Using {device_ctx.__class__.__name__} device context')
    logger.info(f'Using {mouse.__class__.__name__} mouse backend')
    logger.info(f'Using {keyboard.__class__.__name__} keyboard backend')

    return device_ctx, mouse, keyboard


def generate_self_signed_pem(cfg: config.Config):
    # 1. Generate private key
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # 2. Build certificate information
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, 'Pynergy-Client'),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, 'OpenSource'),
    ])

    # 3. Create self-signed certificate
    cert = (
        x509
        .CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow())
        .not_valid_after(
            # Valid for 1 year
            datetime.datetime.utcnow() + datetime.timedelta(days=365)
        )
        .add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        )
        .sign(key, hashes.SHA256())
    )

    # 4. Write to file (merge private key and certificate into the same PEM)
    with open(cfg.pem_path, 'wb') as f:
        # Write private key
        f.write(
            key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )
        # Write certificate
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    print(f'Successfully generated certificate file: {cfg.pem_path}')


def get_or_create_client_cert(cfg: config.Config):
    """
    Check if certificate exists and whether it has expired, regenerate if necessary.
    Returns certificate path.
    """
    should_generate = False

    # 1. Check if file exists
    if not cfg.pem_path.exists():
        print(f'[*] Certificate file {cfg.pem_path} does not exist, generating...')
        should_generate = True
    else:
        # 2. If exists, check if expired
        try:
            with open(cfg.pem_path, 'rb') as f:
                pem_data = f.read()
                # Load certificate object
                cert = x509.load_pem_x509_certificate(pem_data, default_backend())

                # Check expiration time (UTC)
                # Leave 1 day buffer to prevent disconnection at critical point
                remaining_time = cert.not_valid_after - datetime.datetime.utcnow()

                if remaining_time.total_seconds() <= 86400:  # Less than 24 hours
                    print(
                        f'[!] Certificate is about to expire or has expired ({remaining_time.days} days remaining), regenerating...'
                    )
                    should_generate = True
                else:
                    print(
                        f'[+] Certificate is valid, valid until: {cert.not_valid_after} ({remaining_time.days} days remaining)'
                    )
        except Exception as e:
            print(f'[!] Failed to parse certificate: {e}, will attempt to regenerate.')
            should_generate = True

    # 3. Execute generation logic
    if should_generate:
        generate_self_signed_pem(cfg)

    return cfg.pem_path


def get_fingerprint(pem_path):
    with open(pem_path, 'rb') as f:
        data = f.read()
        cert_data = x509.load_pem_x509_certificate(data)
        fingerprint = hashlib.sha256(cert_data.public_bytes(serialization.Encoding.DER)).hexdigest()
    return fingerprint.upper()


def setup_ssl_context(cfg: config.Config) -> ssl.SSLContext | None:
    if not cfg.tls and not cfg.mtls:
        return None

    cert_file = get_or_create_client_cert(cfg)

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    # Load this auto-generated (or existing) certificate
    if cfg.mtls:
        context.load_cert_chain(certfile=cert_file)

    # For Deskflow self-signed environment, these two lines are usually required
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    return context


async def validate_cert(writer, cfg: config.Config):
    if not cfg.tls and not cfg.mtls:
        return
    if cfg.tls_trust:
        return
    transport = writer.transport
    ssl_obj = transport.get_extra_info('ssl_object')
    cert_bin = ssl_obj.getpeercert(binary_form=True)

    current_fingerprint = hashlib.sha256(cert_bin).hexdigest().upper()
    known_hosts_file = cfg.pem_path.parent / 'known_hosts.json'
    if not known_hosts_file.exists():
        with open(known_hosts_file, 'w+') as f:
            json.dump({}, f)

    with open(known_hosts_file, 'r') as f:
        known_hosts = json.load(f)

    if cfg.server not in known_hosts.keys():
        typer.echo(f'Found new certificate fingerprint: {current_fingerprint}')
        confirm = await questionary.confirm('Trust and continue? ', default=True).ask_async()
        if confirm:
            known_hosts[cfg.server] = current_fingerprint
            with open(known_hosts_file, 'w') as f:
                json.dump(known_hosts, f, indent=2)
        else:
            writer.close()
            raise Exception('User cancelled trust')

    elif known_hosts[cfg.server] != current_fingerprint:
        typer.echo('Warning: Server fingerprint changed, potential security risk!')
        typer.echo(f'Current fingerprint: {current_fingerprint}')
        typer.echo(f'Known fingerprint: {known_hosts[cfg.server]}')
        confirm = await questionary.confirm('Trust and continue? ', default=False).ask_async()
        if confirm:
            known_hosts[cfg.server] = current_fingerprint
            with open(known_hosts_file, 'w') as f:
                json.dump(known_hosts, f, indent=2)
        else:
            writer.close()
            raise Exception('Warning: Server fingerprint changed, potential security risk!')
