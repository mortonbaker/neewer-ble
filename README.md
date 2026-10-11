# neewer-ble

Control **Neewer MS60C** studio lights over Bluetooth LE from Python (Windows, macOS or Linux, via
[bleak](https://github.com/hbldh/bleak)), without the phone app. There's a small CLI, presets, an optional
background service that keeps the connections open so commands land in about 100 ms, and the tools used to
reverse-engineer the protocol.

**The protocol is written up in [docs/PROTOCOL.md](docs/PROTOCOL.md).** The short version: MS60C commands carry the
light's own MAC address inside the frame, and the older MAC-less commands that other write-ups describe are
acknowledged and then ignored.

## Setup

```
pip install bleak
python tools/scan_nw.py                  # find your lights' MACs
cp lights.example.json lights.json       # then put your MACs and names in it
python tools/color_ident.py MAC1 MAC2    # paints them red / green / ... so you know which is which
```

## Use

```
python neewer.py list
python neewer.py all on
python neewer.py key cct 5600 80         # kelvin, brightness %   [green/magenta -50..50]
python neewer.py left,right hsi 220 100 70
python neewer.py preset talk             # from presets.json
python neewer.py status                  # neewerd: which lights are connected
```

Output is one line per light, `name OK` or `name FAIL reason`, and the exit code is 1 if any light failed,
so scripts and Stream Deck buttons can rely on it. The light names in `presets.json` have to match the ones in your `lights.json`.

## neewerd: fast switching

Each fresh BLE connect costs 4–30 s. `neewerd.py` keeps a connection open to every light and serves `neewer.py` on
`127.0.0.1:8791`, which brings a command down to about 100 ms. `neewer.py` uses it automatically when it's running,
and connects directly when it isn't; the output is the same either way. When a light drops, neewerd listens for it
and reconnects as soon as it advertises again. A power-cycled MS60C only advertises after you press its button.

Run it in the background, for example on Windows at logon:

```
pythonw neewerd.py
```

Log: `neewerd.log`. Only one copy runs at a time; a second copy exits because the port is taken.

## Status

Tested on 3× MS60C from Windows 11, controlling power, CCT and HSI. Other models: unknown. PRs with confirmations are welcome.

Unofficial; not affiliated with Neewer. MIT licensed.
