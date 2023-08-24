import asyncio
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


async def handle_client(reader, writer):
    data = await reader.read(4096)
    first_line = data.split(b"\n")[0]
    method, target_host, _ = first_line.split(b" ")

    if method == b"CONNECT":
        target_host, target_port = target_host.split(b":")
        target_port = int(target_port)

        logger.info(f"coming request: {target_host}:{target_port}")

        try:
            target_reader, target_writer = await asyncio.open_connection(
                target_host, target_port
            )

            writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            await writer.drain()

            async def forward(src, dst):
                while True:
                    data = await src.read(4096)
                    if len(data) == 0:
                        break
                    dst.write(data)
                    await dst.drain()

            await asyncio.gather(
                forward(reader, target_writer), forward(target_reader, writer)
            )
        except Exception as e:
            print(f"Error: {e}")

        writer.close()
    else:
        writer.close()


async def main():
    bind_ip = "0.0.0.0"
    bind_port = 8888

    server = await asyncio.start_server(handle_client, bind_ip, bind_port)

    print(f"[*] Listening on {bind_ip}:{bind_port}")

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
