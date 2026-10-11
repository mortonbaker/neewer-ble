import asyncio, sys, time
from bleak import BleakClient
WRITE  = "69400002-b5a3-f393-e0a9-e50e24dcca99"
NOTIFY = "69400003-b5a3-f393-e0a9-e50e24dcca99"
def pkt(tag, *p):
    b = [0x78, tag, len(p), *p]; return bytes(b + [sum(b) & 0xFF])
def macpkt(tag, mac, sub, *vals):
    m = [int(x, 16) for x in mac.split(":")]
    return pkt(tag, *m, sub, *vals)
async def blink(addr, n):
    OFF, ON = macpkt(0x8D, addr, 0x81, 0x02), macpkt(0x8D, addr, 0x81, 0x01)
    print(f"== {addr}: {n} blink(s) at {time.strftime('%H:%M:%S')}")
    async with BleakClient(addr, timeout=30) as c:
        await c.start_notify(NOTIFY, lambda _, d: print("   RX", d.hex(" ")))
        for i in range(n):
            await c.write_gatt_char(WRITE, OFF, response=False); print("   TX OFF", OFF.hex(" ")); await asyncio.sleep(1.5)
            await c.write_gatt_char(WRITE, ON,  response=False); print("   TX ON ", ON.hex(" "));  await asyncio.sleep(1.5)
async def main():
    for n, a in enumerate(sys.argv[1:], 1):
        for attempt in range(3):
            try: await blink(a, n); break
            except Exception as e: print(f"   attempt {attempt+1} FAILED {a}: {e!r}")
        await asyncio.sleep(3)
if __name__ == "__main__": asyncio.run(main())
