import asyncio, sys, time
from bleak import BleakClient

WRITE  = "69400002-b5a3-f393-e0a9-e50e24dcca99"
NOTIFY = "69400003-b5a3-f393-e0a9-e50e24dcca99"
ALT_N  = "7f510005-b5a3-f393-e0a9-e50e24dcca9e"
T0 = time.time()

def pkt(tag, *payload):
    b = [0x78, tag, len(payload), *payload]
    return bytes(b + [sum(b) & 0xFF])

def log(src):
    return lambda _, data: print(f"  [{time.time()-T0:6.2f}] RX {src}: {data.hex(' ')}")

async def send(c, label, data, wait=1.5):
    print(f"[{time.time()-T0:6.2f}] TX {label}: {data.hex(' ')}")
    await c.write_gatt_char(WRITE, data, response=False)
    await asyncio.sleep(wait)

async def main(addr):
    async with BleakClient(addr, timeout=30) as c:
        await c.start_notify(NOTIFY, log("6940"))
        try: await c.start_notify(ALT_N, log("7f51"))
        except Exception as e: print("alt notify failed:", e)
        await send(c, "status query 0x84", pkt(0x84))
        await send(c, "channel query 0x85", pkt(0x85))
        await send(c, "POWER OFF", pkt(0x81, 0x02), 2)
        await send(c, "POWER ON",  pkt(0x81, 0x01), 2)
        await send(c, "status query 0x84", pkt(0x84))

asyncio.run(main(sys.argv[1]))
