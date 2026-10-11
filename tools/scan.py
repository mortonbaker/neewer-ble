import asyncio
from bleak import BleakScanner

async def main():
    found = await BleakScanner.discover(timeout=12, return_adv=True)
    for addr, (dev, adv) in sorted(found.items(), key=lambda x: -x[1][1].rssi):
        name = adv.local_name or dev.name or ""
        tag = "  <-- NEEWER?" if any(k in name.upper() for k in ("NEEWER","NW-","NWR","SL","RGB","CB","GL")) else ""
        print(f"{addr}  rssi={adv.rssi:4}  name={name!r}  svcs={adv.service_uuids}  mfr={ {k:v.hex() for k,v in adv.manufacturer_data.items()} }{tag}")

asyncio.run(main())
