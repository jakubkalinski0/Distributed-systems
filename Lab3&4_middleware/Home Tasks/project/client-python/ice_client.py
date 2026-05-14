from __future__ import annotations

import argparse
import os
import sys
import time
from typing import Iterable

_GEN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "generated")
if _GEN not in sys.path:
    sys.path.insert(0, _GEN)

import Ice
import smarthome


def _ts() -> str:
    return time.strftime("%H:%M:%S")


def log(msg: str) -> None:
    print(f"[{_ts()}][client] {msg}")


def connect_buildings(communicator: Ice.Communicator, proxies: Iterable[str]):
    buildings = []
    for s in proxies:
        try:
            base = communicator.stringToProxy(s)
            building = smarthome.BuildingPrx.checkedCast(base)
            if building is None:
                log(f"NIE rozpoznano interfejsu Building dla {s!r}")
                continue
            name = building.getName()
            log(f"connected to '{name}' via {s!r}")
            buildings.append((name, building))
        except Ice.LocalException as ex:
            log(f"polaczenie z {s!r} nieudane: {type(ex).__name__}: {ex}")
    return buildings


def list_all(buildings) -> dict:
    print()
    index: dict[str, tuple[str, smarthome.BuildingPrx]] = {}
    for name, b in buildings:
        try:
            devices = b.listDevices()
        except Ice.LocalException as ex:
            log(f"[{name}] listDevices nie powiodlo sie: {ex}")
            continue
        print(f"=== {name} ===")
        for d in devices:
            print(f"  {d.id:<10}  kind={d.kind:<11}  power={d.power.name}")
            index[d.id] = (name, b)
    print()
    return index


def cast_to_concrete(base: smarthome.DevicePrx):
    cl = smarthome.ColorLightPrx.checkedCast(base)
    if cl is not None:
        return "ColorLight", cl
    li = smarthome.LightPrx.checkedCast(base)
    if li is not None:
        return "Light", li
    th = smarthome.ThermostatPrx.checkedCast(base)
    if th is not None:
        return "Thermostat", th
    ca = smarthome.CameraPrx.checkedCast(base)
    if ca is not None:
        return "Camera", ca
    return "Device", base


def show_device_menu(kind: str) -> str:
    common = [
        "info                         - DeviceInfo (id, kind, power)",
        "power on                     - setPower(On)",
        "power off                    - setPower(Off)",
    ]
    specific = {
        "Light": [
            "brightness <0..100>          - setBrightness",
            "brightness?                  - getBrightness",
        ],
        "ColorLight": [
            "brightness <0..100>          - setBrightness",
            "brightness?                  - getBrightness",
            "color <r> <g> <b>            - setColor (kazdy 0..255)",
            "color?                       - getColor",
        ],
        "Thermostat": [
            "target <celsius>             - setTarget (-50..50)",
            "target?                      - getTarget",
            "mode <ModeOff|Heating|Cooling> - setMode",
            "mode?                        - getMode",
        ],
        "Camera": [
            "ptz <pan> <tilt> <zoom>      - setPTZ",
            "ptz?                         - getPTZ",
            "snapshot                     - po 5. wywolaniu rzuca DeviceUnavailable",
        ],
    }
    items = ["Operacje:"] + common + specific.get(kind, []) + ["back                         - powrot do menu glownego"]
    return "  " + "\n  ".join(items)


def operate(device_id: str, kind: str, prx) -> None:
    print()
    print(f"--- operating on {device_id} ({kind}) ---")
    print(show_device_menu(kind))
    while True:
        try:
            line = input(f"{device_id}> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not line:
            continue
        if line in ("back", "quit", "q"):
            return

        parts = line.split()
        cmd = parts[0]
        args = parts[1:]
        try:
            if cmd == "info":
                _print_info(prx.info())
            elif cmd == "power" and len(args) == 1:
                state = smarthome.PowerState.On if args[0].lower() == "on" else smarthome.PowerState.Off
                prx.setPower(state)
                print(f"  -> power = {state.name}")
            elif cmd == "brightness?" and kind in ("Light", "ColorLight"):
                print(f"  -> brightness = {prx.getBrightness()}")
            elif cmd == "brightness" and kind in ("Light", "ColorLight") and len(args) == 1:
                prx.setBrightness(int(args[0]))
                print("  -> OK")
            elif cmd == "color?" and kind == "ColorLight":
                c = prx.getColor()
                print(f"  -> color = ({c.r},{c.g},{c.b})")
            elif cmd == "color" and kind == "ColorLight" and len(args) == 3:
                c = smarthome.Color(int(args[0]), int(args[1]), int(args[2]))
                prx.setColor(c)
                print("  -> OK")
            elif cmd == "target?" and kind == "Thermostat":
                print(f"  -> target = {prx.getTarget():.1f} C")
            elif cmd == "target" and kind == "Thermostat" and len(args) == 1:
                prx.setTarget(float(args[0]))
                print("  -> OK")
            elif cmd == "mode?" and kind == "Thermostat":
                print(f"  -> mode = {prx.getMode().name}")
            elif cmd == "mode" and kind == "Thermostat" and len(args) == 1:
                m = getattr(smarthome.HvacMode, args[0], None)
                if m is None:
                    print(f"  ! unknown HvacMode: {args[0]}")
                    continue
                prx.setMode(m)
                print("  -> OK")
            elif cmd == "ptz?" and kind == "Camera":
                p = prx.getPTZ()
                print(f"  -> PTZ pan={p.pan:.1f} tilt={p.tilt:.1f} zoom={p.zoom}")
            elif cmd == "ptz" and kind == "Camera" and len(args) == 3:
                p = smarthome.PTZ(float(args[0]), float(args[1]), int(args[2]))
                prx.setPTZ(p)
                print("  -> OK")
            elif cmd == "snapshot" and kind == "Camera":
                snap = prx.snapshot()
                print(f"  -> snapshot id = {snap}")
            else:
                print("  ! nieznana komenda lub zla liczba argumentow")
                print(show_device_menu(kind))
        except smarthome.InvalidParameter as ex:
            print(f"  ! REMOTE InvalidParameter: field='{ex.field}' reason='{ex.reason}'")
        except smarthome.DeviceUnavailable as ex:
            print(f"  ! REMOTE DeviceUnavailable: reason='{ex.reason}'")
        except smarthome.DeviceError as ex:
            print(f"  ! REMOTE DeviceError: reason='{ex.reason}'")
        except ValueError as ex:
            print(f"  ! local ValueError: {ex}")
        except Ice.LocalException as ex:
            print(f"  ! Ice.LocalException: {type(ex).__name__}: {ex}")


def _print_info(d: smarthome.DeviceInfo) -> None:
    print(f"  -> id={d.id} kind={d.kind} power={d.power.name}")


def main_menu(buildings) -> None:
    index = list_all(buildings)
    while True:
        try:
            print("Glowne menu:")
            print("  [l] list devices (oba serwery)")
            print("  [d] <device_id>  (skroty: 'd light-1', 'light-1')")
            print("  [q] quit")
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not line:
            continue
        parts = line.split()
        cmd = parts[0]
        if cmd in ("l", "list"):
            index = list_all(buildings)
        elif cmd in ("q", "quit", "exit"):
            return
        elif cmd in ("d", "device") and len(parts) >= 2:
            _open_device(parts[1], buildings, index)
        elif cmd in index:
            _open_device(cmd, buildings, index)
        else:
            print(f"  ! nieznane polecenie: {line!r}")


def _open_device(device_id: str, buildings, index) -> None:
    if device_id not in index:
        index.update(list_all(buildings))
        if device_id not in index:
            print(f"  ! brak urzadzenia o id={device_id}")
            return
    name, building = index[device_id]
    try:
        base = building.getDevice(device_id)
    except smarthome.DeviceError as ex:
        print(f"  ! [{name}] DeviceError: {ex.reason}")
        return
    kind, concrete = cast_to_concrete(base)
    if concrete is base and kind == "Device":
        print(f"  ! [{name}] {device_id}: nie udalo sie wykryc podtypu (otrzymano czysty Device)")
        return
    operate(device_id, kind, concrete)


def main() -> int:
    parser = argparse.ArgumentParser(description="Ice CLI client for smarthome (A1)")
    parser.add_argument(
        "--proxy",
        action="append",
        required=True,
        help='stringified proxy do Building, np. "building:tcp -h localhost -p 10000"',
    )
    args, ice_args = parser.parse_known_args()

    with Ice.initialize() as communicator:
        buildings = connect_buildings(communicator, args.proxy)
        if not buildings:
            log("brak polaczenia z jakimkolwiek serwerem - koncze")
            return 1
        main_menu(buildings)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
