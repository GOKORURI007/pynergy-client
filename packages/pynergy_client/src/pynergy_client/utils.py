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
    # 1. 生成私钥
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # 2. 构建证书信息
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, u"Pynergy-Client"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"OpenSource"),
    ])

    # 3. 创建自签名证书
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.utcnow()
    ).not_valid_after(
        # 有效期 1 年
        datetime.datetime.utcnow() + datetime.timedelta(days=365)
    ).add_extension(
        x509.BasicConstraints(ca=False, path_length=None), critical=True,
    ).sign(key, hashes.SHA256())

    # 4. 写入文件 (合并私钥和证书到同一个 PEM)
    with open(cfg.pem_path, "wb") as f:
        # 写入私钥
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ))
        # 写入证书
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    print(f"成功生成证书文件: {cfg.pem_path}")


def get_or_create_client_cert(cfg: config.Config):
    """
    检测证书是否存在及是否过期，必要时重新生成。
    返回证书路径。
    """
    should_generate = False

    # 1. 检查文件是否存在
    if not cfg.pem_path.exists():
        print(f"[*] 证书文件 {cfg.pem_path} 不存在，准备生成...")
        should_generate = True
    else:
        # 2. 如果存在，检查是否过期
        try:
            with open(cfg.pem_path, "rb") as f:
                pem_data = f.read()
                # 加载证书对象
                cert = x509.load_pem_x509_certificate(pem_data, default_backend())

                # 检查过期时间 (UTC)
                # 留出 1 天的缓冲期，防止临界点断连
                remaining_time = cert.not_valid_after - datetime.datetime.utcnow()

                if remaining_time.total_seconds() <= 86400:  # 小于 24 小时
                    print(f"[!] 证书即将过期或已过期（剩余 {remaining_time.days} 天），重新生成...")
                    should_generate = True
                else:
                    print(
                        f"[+] 证书有效，有效期至: {cert.not_valid_after} (剩余 {remaining_time.days} 天)")
        except Exception as e:
            print(f"[!] 证书解析失败: {e}，将尝试重新生成。")
            should_generate = True

    # 3. 执行生成逻辑
    if should_generate:
        generate_self_signed_pem(cfg)

    return cfg.pem_path


def get_fingerprint(pem_path):
    with open(pem_path, "rb") as f:
        data = f.read()
        cert_data = x509.load_pem_x509_certificate(data)
        fingerprint = hashlib.sha256(cert_data.public_bytes(serialization.Encoding.DER)).hexdigest()
    return fingerprint.upper()


def setup_ssl_context(cfg: config.Config) -> ssl.SSLContext | None:
    if not cfg.tls and not cfg.mtls:
        return None

    cert_file = get_or_create_client_cert(cfg)

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    # 加载这个自动生成的（或现有的）证书
    if cfg.mtls:
        context.load_cert_chain(certfile=cert_file)

    # 对于 Deskflow 的自签名环境，通常需要这两行
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
        typer.echo(f"发现新证书指纹: {current_fingerprint}")
        confirm = await questionary.confirm("是否信任并继续? ", default=True).ask_async()
        if confirm:
            known_hosts[cfg.server] = current_fingerprint
            with open(known_hosts_file, 'w') as f:
                json.dump(known_hosts, f, indent=2)
        else:
            writer.close()
            raise Exception("用户取消信任")

    elif known_hosts[cfg.server] != current_fingerprint:
        typer.echo(f"警告：服务端指纹变更，可能存在风险！")
        typer.echo(f"当前指纹: {current_fingerprint}")
        typer.echo(f"已知指纹: {known_hosts[cfg.server]}")
        confirm = await questionary.confirm("是否信任并继续? ", default=False).ask_async()
        if confirm:
            known_hosts[cfg.server] = current_fingerprint
            with open(known_hosts_file, 'w') as f:
                json.dump(known_hosts, f, indent=2)
        else:
            writer.close()
            raise Exception("警告：服务端指纹变更，可能存在风险！")
