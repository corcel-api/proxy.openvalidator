import asyncio
import itertools
import aiohttp
import base64
import hashlib
import hmac
import logging
import os

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

EXPECTED_USERNAME = os.getenv("PROXY_USERNAME")
EXPECTED_PASSWORD = os.getenv("PROXY_PASSWORD")
EXPECTED_USERNAME_HASH = (
    hashlib.sha512(EXPECTED_USERNAME.encode()).digest() if EXPECTED_USERNAME else None
)
EXPECTED_PASSWORD_HASH = (
    hashlib.sha512(EXPECTED_PASSWORD.encode()).digest() if EXPECTED_PASSWORD else None
)

request_id_counter = itertools.count()


def remove_hop_headers(headers):
    headers = headers.copy()
    for header in [
        "Connection",
        "Keep-Alive",
        "Proxy-Authenticate",
        "Proxy-Authorization",
        "Te",
        "Trailers",
        "Transfer-Encoding",
        "Upgrade",
    ]:
        if header in headers:
            del headers[header]
    return headers


def parse_basic_auth(auth_str):
    if not auth_str:
        return "", "", False
    prefix = b"Basic "
    if not auth_str.startswith(prefix):
        return "", "", False
    try:
        decoded_str = base64.b64decode(auth_str[len(prefix) :]).decode()
        username, password = decoded_str.split(":")
        return username, password, True
    except Exception:
        return "", "", False


def handle_authentication(auth_header):
    if not EXPECTED_USERNAME or not EXPECTED_PASSWORD:
        return True
    username, password, ok = parse_basic_auth(auth_header)
    if not ok:
        return False
    username_hash = hashlib.sha512(username.encode()).digest()
    password_hash = hashlib.sha512(password.encode()).digest()
    equal_username = hmac.compare_digest(username_hash, EXPECTED_USERNAME_HASH)
    equal_password = hmac.compare_digest(password_hash, EXPECTED_PASSWORD_HASH)
    return equal_username and equal_password


async def handle_client(reader, writer):
    request_id = next(request_id_counter)
    logger.info(f"{request_id}: New request")

    try:
        data = await reader.read(4096)
        first_line = data.split(b"\n")[0]
        method, target_host, _ = first_line.split(b" ")

        auth_header = next(
            (
                line.split(b": ", 1)[1]
                for line in data.split(b"\r\n")
                if line.lower().startswith(b"proxy-authorization: ")
            ),
            None,
        )
        if not handle_authentication(auth_header):
            logger.info(f"{request_id}: Authentication failed")
            writer.write(
                b"HTTP/1.1 407 Proxy Authentication Required\r\nProxy-Authenticate: Basic\r\n\r\n"
            )
            await writer.drain()
            writer.close()
            return

        if method != b"CONNECT":
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method.decode(), target_host.decode()
                ) as resp:
                    writer.write(f"HTTP/1.1 {resp.status} {resp.reason}\r\n".encode())
                    headers = remove_hop_headers(resp.headers)
                    for header, value in headers.items():
                        writer.write(f"{header}: {value}\r\n".encode())
                    writer.write(b"\r\n")
                    await writer.drain()
                    body = await resp.read()
                    writer.write(body)
                    await writer.drain()
        else:
            target_host, target_port = target_host.split(b":")
            target_port = int(target_port)

            logger.info(
                f"{request_id} coming request: {target_host.decode()}:{target_port}"
            )

            try:
                target_reader, target_writer = await asyncio.open_connection(
                    target_host.decode(), target_port
                )
            except Exception as e:
                logger.error(f"{request_id} Error: {e}")
                return

            writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            await writer.drain()

            async def forward(src, dst):
                while True:
                    data = await src.read(4096)
                    if len(data) == 0:
                        dst.close()
                        break
                    try:
                        dst.write(data)
                        await dst.drain()
                    except Exception as e:
                        logger.error(f"{request_id} Error: {e}")
                        break

            await asyncio.gather(
                forward(reader, target_writer),
                forward(target_reader, writer),
            )
    except Exception as e:
        logger.error(f"{request_id} Error: {e}")
    finally:
        writer.close()

    try:
        while await reader.read(4096):
            pass
    except Exception as e:
        logger.error(f"{request_id} Error: {e}")

    logger.info(f"{request_id}: Request done")


async def main():
    bind_ip = "0.0.0.0"
    bind_port = 8888

    server = await asyncio.start_server(handle_client, bind_ip, bind_port)

    logger.info(f"[*] Listening on {bind_ip}:{bind_port}")

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
