"""Browser test server: records commands without controlling the real desktop."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import receiver
from input_control import InputController

class RecordingController(InputController):
    def __init__(self):
        super().__init__(sender=lambda items: None)
    def execute(self, payload):
        result = super().execute(payload)
        print(json.dumps(payload, ensure_ascii=True), flush=True)
        return result

if __name__ == "__main__":
    server = receiver.create_server(host="127.0.0.1", port=53515, token="browser-test-token", controller=RecordingController())
    print("BROWSER_TEST_READY", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
