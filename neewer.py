"""Neewer MS60C BLE control (MAC-tagged "Infinity" protocol).

  neewer.py <light|all> on|off
  neewer.py <light|all> cct <kelvin> <bri%> [gm -50..50]
  neewer.py <light|all> hsi <hue 0-360> <sat%> <bri%>
  neewer.py preset <name>        (from presets.json)
  neewer.py list
  neewer.py status               (neewerd: which lights are connected / waiting)

Uses the neewerd service (persistent BLE connections, 127.0.0.1:8791) when it is running,
otherwise connects directly. Output and exit codes are identical either way.
Frame: 78 | tag | len | payload | sum&0xFF. Payload = MAC(6) + subtag + values.
"""
import asyncio, json, socket, sys
from pathlib import Path

WRITE = "69400002-b5a3-f393-e0a9-e50e24dcca99"
_CFG = Path(__file__).parent / "lights.json"
if not _CFG.exists(): raise SystemExit("no lights.json: copy lights.example.json to lights.json and put your lights' MACs in it (tools/scan_nw.py finds them)")
LIGHTS = json.loads(_CFG.read_text())
PRESETS = json.loads((Path(__file__).parent / "presets.json").read_text())
DAEMON = ("127.0.0.1", 8791)

def frame(tag, *payload):
    b = [0x78, tag, len(payload), *payload]
    return bytes(b + [sum(b) & 0xFF])

def cmd(tag, mac, sub, *vals):
    return frame(tag, *(int(x, 16) for x in mac.split(":")), sub, *vals)

def power(mac, on):            return cmd(0x8D, mac, 0x81, 0x01 if on else 0x02)
def cct(mac, k, bri, gm=0):    return cmd(0x90, mac, 0x87, clamp(bri, 0, 100), clamp(round(k / 100), 25, 100), clamp(gm, -50, 50) + 50, 0x04)
def hsi(mac, hue, sat, bri):   hue = clamp(hue, 0, 360); return cmd(0x8F, mac, 0x86, hue & 0xFF, hue >> 8, clamp(sat, 0, 100), clamp(bri, 0, 100), 0x00)
def clamp(v, lo, hi):          return max(lo, min(hi, int(v)))

def spec_packets(mac, spec):
    op, *a = spec
    if op in ("on", "off"): return [power(mac, op == "on")]
    if op == "cct":         return [cct(mac, *a)]
    if op == "hsi":         return [hsi(mac, *a)]
    raise SystemExit(__doc__)

def plan(argv):
    """argv -> (header line or None, [(light, [packets]), ...], show_hex). Pure: no I/O."""
    if argv[:1] == ["preset"]:
        if len(argv) < 2 or argv[1] not in PRESETS: raise SystemExit(f"presets: {', '.join(PRESETS)}")
        jobs = []
        for n, spec in PRESETS[argv[1]].items():
            mac = LIGHTS[n]["mac"]
            jobs.append((n, ([] if spec[0] == "off" else [power(mac, True)]) + spec_packets(mac, spec)))
        return f"preset {argv[1]}", jobs, False
    targets = list(LIGHTS) if argv[0] == "all" else argv[0].split(",")
    unknown = [t for t in targets if t not in LIGHTS]
    if unknown or len(argv) < 2: raise SystemExit(f"unknown light(s) {unknown}\n{__doc__}")
    spec = [argv[1], *(float(x) for x in argv[2:])]
    return None, [(t, spec_packets(LIGHTS[t]["mac"], spec)) for t in targets], True

def result_line(name, ok, packets, show_hex, err=""):
    if not ok: return f"{name:9} FAIL {err}"
    return f"{name:9} OK   {packets[-1].hex(' ')}" if show_hex else f"{name:9} OK"

async def send_direct(name, packets, show_hex, tries=3):
    from bleak import BleakClient
    mac = LIGHTS[name]["mac"]; err = ""
    for _ in range(tries):
        try:
            async with BleakClient(mac, timeout=20) as c:
                for p in packets:
                    await c.write_gatt_char(WRITE, p, response=False); await asyncio.sleep(0.15)
                return result_line(name, True, packets, show_hex)
        except Exception as e:
            err = repr(e)
    return result_line(name, False, packets, show_hex, err)

def via_daemon(argv):
    """Returns (lines, code) from neewerd, or None if it isn't running."""
    try:
        with socket.create_connection(DAEMON, timeout=0.5) as s:
            s.settimeout(60)
            s.sendall((json.dumps(argv) + "\n").encode())
            buf = b""
            while not buf.endswith(b"\n"):
                chunk = s.recv(65536)
                if not chunk: break
                buf += chunk
        r = json.loads(buf)
        return r["lines"], r["code"]
    except (OSError, ValueError):
        return None

async def main(argv):
    if not argv or argv[0] == "list":
        for n, l in LIGHTS.items(): print(f"{n:9} {l['mac']}  {l['model']}  {l['note']}")
        print("presets:", ", ".join(PRESETS))
        return 0
    if argv == ["status"]:
        r = via_daemon(argv)
        print("\n".join(r[0]) if r else "neewerd not running (commands connect directly, 4-30 s each)")
        return 0 if r else 1
    header, jobs, show_hex = plan(argv)          # validate before touching anything
    r = via_daemon(argv)
    if r is not None:
        lines, code = r
        print("\n".join(lines)); return code
    results = await asyncio.gather(*(send_direct(n, pk, show_hex) for n, pk in jobs))
    if header: print(header)
    print("\n".join(results))
    return 1 if any(" FAIL " in x for x in results) else 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1:])))
