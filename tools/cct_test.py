"""Send two CCT frames (3200K 20%, then 5600K 100%) to one light.  python tools/cct_test.py <MAC>"""
import asyncio, sys, time
from bleak import BleakClient
from blink import WRITE, macpkt
def cct(mac, bri, k100, gm=0):  # tag 0x90, subtag 0x87: bri, cct/100, gm+50, dimming curve 4
    return macpkt(0x90, mac, 0x87, bri, k100, gm + 50, 0x04)
async def main(mac):
    async with BleakClient(mac, timeout=30) as c:
        for label, p in [("3200K 20%", cct(mac, 20, 32)), ("5600K 100%", cct(mac, 100, 56))]:
            print(time.strftime('%H:%M:%S'), "TX", label, p.hex(" "))
            await c.write_gatt_char(WRITE, p, response=False); await asyncio.sleep(4)
if __name__ == "__main__": asyncio.run(main(sys.argv[1]))
