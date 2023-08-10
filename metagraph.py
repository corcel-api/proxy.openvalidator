import logging
import time
import bittensor
from typing import List, Optional
from threading import Thread, Event

SUPPORTED_SUBNETWORKS: List[int] = [1, 11]


class MetagraphSyncer:
    def __init__(
        self, netuid: int, rest_seconds: int = 60, extra_fail_rest_seconds: int = 60
    ):
        self.last_sync_success = None
        self.netuid = netuid
        self.is_syncing = False
        self.rest_seconds = rest_seconds
        self.extra_fail_rest_seconds = extra_fail_rest_seconds
        self.metagraph: Optional[bittensor.metagraph] = None

    def sync(self):
        subtensor = bittensor.subtensor()
        self.is_syncing = True
        try:
            sync_start = time.time()
            metagraph: bittensor.metagraph = subtensor.metagraph(netuid=self.netuid)
            self.metagraph = metagraph
            self.last_sync_success = time.time()
            logging.info(
                f"Synced metagraph for netuid {self.netuid} (took {self.last_sync_success - sync_start:.2f} seconds)",
            )
            return metagraph
        except Exception as e:
            logging.warning("Could not sync metagraph: ", e)
            raise e  # Reraise the exception to be handled by the caller
        finally:
            self.is_syncing = False
            return None

    def start_sync_thread(self):
        self.last_sync_success = time.time()

        # Run in a separate thread
        def loop():
            while True:
                try:
                    self.sync()
                except Exception as e:
                    time.sleep(self.extra_fail_rest_seconds)
                time.sleep(self.rest_seconds)

        thread = Thread(target=loop, daemon=True)
        thread.start()
        logging.info("Started metagraph sync thread")
        return thread


metagraph_syncers: dict[int, MetagraphSyncer] = {}
metagraph_sync_event = Event()


for netuid in SUPPORTED_SUBNETWORKS:
    print("syncing %s" % netuid)
    metagraph_syncer = MetagraphSyncer(netuid)
    metagraph_syncers[netuid] = metagraph_syncer
    print("synced %s" % netuid)

metagraph_sync_event.set()
