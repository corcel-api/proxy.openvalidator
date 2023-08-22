import socket
import logging
import asyncio
from fastapi import FastAPI, Request, HTTPException, Response
from starlette.responses import StreamingResponse

app = FastAPI()
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

id_counter = 0


async def pipe(src, dst):
    while True:
        data = await src.recv(4096)
        if not data:
            break
        await dst.sendall(data)


@app.route("/{host}:{port}", methods=["CONNECT"])
async def proxy(request: Request, host: str, port: int):
    global id_counter
    id_counter += 1
    current_id = id_counter
    logger.info(f"{current_id} - request for {host}:{port}")

    # Initial connection confirmation
    response = Response(status_code=200)
    await response.send()

    try:
        reader, writer = await asyncio.open_connection(host, port)
    except Exception as e:
        logger.error(f"{current_id} - dial failed {e}")
        raise HTTPException(status_code=503, detail="Dial failed")

    client_reader, client_writer = await request.legacy_stream()

    asyncio.create_task(pipe(client_reader, writer))
    asyncio.create_task(pipe(reader, client_writer))

    return StreamingResponse(content=b"")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8888)
 