import asyncio, sys
from bleak import BleakClient

async def main(addr):
    async with BleakClient(addr, timeout=30) as c:
        print("connected", addr, "mtu", c.mtu_size)
        for s in c.services:
            print(f"SVC {s.uuid}  {s.description}")
            for ch in s.characteristics:
                val = ""
                if "read" in ch.properties:
                    try: val = (await c.read_gatt_char(ch)).hex()
                    except Exception as e: val = f"<{e}>"
                print(f"  CHR {ch.uuid} h={ch.handle} {ch.properties} {val}")
                for d in ch.descriptors:
                    print(f"    DSC {d.uuid} h={d.handle}")

asyncio.run(main(sys.argv[1]))
