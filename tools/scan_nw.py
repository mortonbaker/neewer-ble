import asyncio, sys
from bleak import BleakScanner
seen = {}
def cb(dev, adv):
    name = adv.local_name or dev.name or ""
    if "NW" in name.upper() or "NEEWER" in name.upper() or 63340 in adv.manufacturer_data:
        prev = seen.get(dev.address)
        if not prev or adv.rssi > prev[1]:
            seen[dev.address] = (name, adv.rssi, {k: v.hex() for k, v in adv.manufacturer_data.items()})
async def main(t):
    async with BleakScanner(cb, scanning_mode="active"):
        await asyncio.sleep(t)
    for a, (n, r, m) in sorted(seen.items(), key=lambda x: -x[1][1]):
        print(f"{a}  best_rssi={r:4}  name={n!r}  mfr={m}")
    print(f"{len(seen)} neewer device(s)")
asyncio.run(main(float(sys.argv[1]) if len(sys.argv) > 1 else 30))
