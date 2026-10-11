"""Paint each light a different colour (red, green, blue, ...) so you can tell which MAC is which.
  python tools/color_ident.py AA:BB:CC:DD:EE:01 AA:BB:CC:DD:EE:02 ...
"""
import asyncio, sys, time
from bleak import BleakClient
from blink import WRITE, macpkt
HUES = [(0, "RED"), (120, "GREEN"), (240, "BLUE"), (60, "YELLOW"), (300, "MAGENTA"), (180, "CYAN")]
def hsi(mac, hue, sat=100, bri=60):
    return macpkt(0x8F, mac, 0x86, hue & 0xFF, hue >> 8, sat, bri, 0x00)
async def one(mac, hue, name):
    for attempt in range(3):
        try:
            async with BleakClient(mac, timeout=30) as c:
                p = hsi(mac, hue)
                await c.write_gatt_char(WRITE, p, response=False); await asyncio.sleep(0.5)
                print(f"{time.strftime('%H:%M:%S')} {mac} -> {name}  {p.hex(' ')}"); return
        except Exception as e: print(f"  {mac} attempt {attempt+1} failed: {e!r}")
async def main(macs):
    for mac, (hue, name) in zip(macs, HUES): await one(mac, hue, name)
if __name__ == "__main__": asyncio.run(main(sys.argv[1:]))
