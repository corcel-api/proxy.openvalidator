from fastapi import FastAPI, Request
import httpx

app = FastAPI()

from .models import RequestModel, ResponseModel
from .metagraph import MetagraphSyncer, metagraph_syncers, metagraph_sync_event

print("text: waiting for metagraph synchronization")
metagraph_sync_event.wait()
print("text: metagraph synchronization completed")

# initialize variables
w = bittensor.wallet(name="default")
metagraph_syncer: MetagraphSyncer = metagraph_syncers[1]


@app.post("/proxy/")
async def proxy_request(request: Request):
    # api_url = "https://third-party-api-endpoint.com"

    # Extract original headers
    headers = dict(request.headers)

    # Filter out headers that might cause issues when forwarding. Adjust as needed.
    exclude_headers = ["host", "connection"]
    headers = {k: v for k, v in headers.items() if k.lower() not in exclude_headers}

    data = await request.body()

    async with httpx.AsyncClient() as client:
        # response = await client.post(api_url, headers=headers, data=data)
        # TODO: forward requests to the network
        pass

    return response.json()
