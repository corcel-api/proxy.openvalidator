import socket
import logging
from fastapi import FastAPI, Request, HTTPException
from starlette.responses import StreamingResponse
from threading import Thread

app = FastAPI()
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

id_counter = 0


def pipe(src, dst):
    try:
        while True:
            data = src.recv(4096)
            if not data:
                break
            dst.sendall(data)
    except Exception as e:
        logger.error(e)
    finally:
        src.close()
        dst.close()


@app.route("/{host}:{port}", methods=["CONNECT"])
async def proxy(request: Request, host: str, port: int):
    global id_counter
    id_counter += 1
    current_id = id_counter
    logger.info(f"{current_id} - request for {host}:{port}")

    if request.method != "CONNECT":
        logger.info(f"{current_id} - invalid method {request.method}")
        raise HTTPException(status_code=405, detail="Invalid method")

    try:
        server_conn = socket.create_connection((host, port))
    except Exception as e:
        logger.error(f"{current_id} - dial failed {e}")
        raise HTTPException(status_code=503, detail="Dial failed")

    client_conn = request.client
    t1 = Thread(target=pipe, args=(client_conn, server_conn))
    t2 = Thread(target=pipe, args=(server_conn, client_conn))

    t1.start()
    t2.start()

    t1.join()
    t2.join()

    logger.info(f"{current_id} - request done")
    return StreamingResponse(content=b"")  # Return an empty response


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8888)
