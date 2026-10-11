"""neewerd — keeps BLE connections to every light open so commands land in milliseconds.

  pythonw neewerd.py           (serve on 127.0.0.1:8791; log to neewerd.log)
Protocol: one JSON line = neewer.py argv; reply one JSON line {"lines": [...], "code": 0|1}.
Extra verb: ["status"] -> one line per light: connected / waiting.

Each light has a keeper: while the link is down it listens for the light's advertisement
(a power-cycled MS60C only advertises after its button is pressed) and connects the moment
it appears; while up it watches for drops. Runs at logon via the "neewerd" scheduled task.
"""
import asyncio, json, logging, time
from pathlib import Path
from bleak import BleakClient, BleakScanner
from neewer import LIGHTS, WRITE, DAEMON, plan, result_line

log = logging.getLogger("neewerd")
WAIT_FOR_LINK = 8.0          # seconds a command waits for a light that is mid-reconnect
SCAN_WINDOW = 10.0           # seconds per advertisement listen while a light is down
RADIO: asyncio.Lock | None = None   # one scan/connect at a time: WinRT times out connects while other scans run

class Link:
    def __init__(self, name):
        self.name, self.mac = name, LIGHTS[name]["mac"]
        self.client: BleakClient | None = None
        self.up = asyncio.Event()
        self.lock = asyncio.Lock()
        self.since = time.time()
        self.state = "starting"

    def _set(self, state):
        if state != self.state:
            log.info("%s %s -> %s", self.name, self.state, state)
            self.state, self.since = state, time.time()

    def _dropped(self, _client):
        self.up.clear(); self._set("waiting")

    async def keeper(self):
        while True:
            if self.up.is_set():
                await asyncio.sleep(2)
                if self.client and not self.client.is_connected: self.up.clear(); self._set("waiting")
                continue
            self._set("waiting")
            async with RADIO:
                dev = await BleakScanner.find_device_by_address(self.mac, timeout=SCAN_WINDOW)
                if dev is not None:
                    t = time.perf_counter()
                    try:
                        c = BleakClient(dev, timeout=20, disconnected_callback=self._dropped)
                        await c.connect()
                        self.client = c; self.up.set(); self._set("connected")
                        log.info("%s connected in %.1fs", self.name, time.perf_counter() - t)
                    except Exception as e:
                        log.info("%s seen but connect failed (%r)", self.name, e)
            await asyncio.sleep(0.5)                      # let the other keepers take the radio

    def status_line(self):
        return f"{self.name:9} {self.state:10} for {int(time.time() - self.since)}s"

    async def send(self, packets, show_hex):
        try:
            await asyncio.wait_for(self.up.wait(), WAIT_FOR_LINK)
        except asyncio.TimeoutError:
            return result_line(self.name, False, packets, show_hex, f"not connected ({self.state}; power it on / press its button)")
        async with self.lock:
            try:
                for i, p in enumerate(packets):
                    if i: await asyncio.sleep(0.15)
                    await self.client.write_gatt_char(WRITE, p, response=False)
                return result_line(self.name, True, packets, show_hex)
            except Exception as e:
                self.up.clear(); self._set("waiting")
                return result_line(self.name, False, packets, show_hex, repr(e))

async def main():
    logging.basicConfig(filename=Path(__file__).with_name("neewerd.log"), level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    global RADIO
    RADIO = asyncio.Lock()
    links = {n: Link(n) for n in LIGHTS}

    async def handle(reader, writer):
        try:
            argv = json.loads(await reader.readline())
            t = time.perf_counter()
            if argv == ["status"]:
                lines, code = [l.status_line() for l in links.values()], 0
            else:
                header, jobs, show_hex = plan(argv)
                res = await asyncio.gather(*(links[n].send(pk, show_hex) for n, pk in jobs))
                lines = ([header] if header else []) + list(res)
                code = 1 if any(" FAIL " in x for x in res) else 0
            log.info("%s -> code %d in %.0f ms", argv, code, (time.perf_counter() - t) * 1000)
        except SystemExit as e:
            lines, code = [str(e)], 2
        except Exception as e:
            lines, code = [f"neewerd error {e!r}"], 1
        writer.write((json.dumps({"lines": lines, "code": code}) + "\n").encode())
        await writer.drain(); writer.close()

    try:
        server = await asyncio.start_server(handle, *DAEMON)    # bind first: a second copy exits here
    except OSError as e:
        log.error("port %d busy (%s) - another neewerd is running; exiting", DAEMON[1], e); return
    log.info("listening on %s:%d", *DAEMON)
    for l in links.values(): asyncio.create_task(l.keeper())
    async with server: await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())
