import websockets
import json
import logging

logger = logging.getLogger(__name__)

class RustRCONClient:
    def __init__(self, host: str, port: int, password: str):
        self.host = host
        self.port = port
        self.password = password
        self.ws = None

    async def connect(self):
        try:
            uri = f"ws://{self.host}:{self.port}/{self.password}"
            self.ws = await websockets.connect(uri)
            logger.info(f"Connected to RCON {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to RCON {self.host}:{self.port} - {e}")
            return False

    async def send_command(self, command: str, identifier: int = 1):
        if not self.ws:
            return None
            
        packet = {
            "Identifier": identifier,
            "Message": command,
            "Name": "WebRcon"
        }
        try:
            await self.ws.send(json.dumps(packet))
            response = await self.ws.recv()
            return json.loads(response)
        except Exception as e:
            logger.error(f"Error sending RCON command: {e}")
            return None

    async def close(self):
        if self.ws:
            await self.ws.close()
            self.ws = None
