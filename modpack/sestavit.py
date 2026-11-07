#!/usr/bin/env python3
"""Sestaví modpack pro hráče (soubor .mrpack pro Modrinth App / Prism Launcher).

Obsahuje: Fabric loader, Fabric API, Simple Voice Chat a adresu serveru v seznamu serverů.
Verze modů bere z Modrinthu stejně jako server (nejnovější pro VERSION, včetně beta).

Použití:  python3 modpack/sestavit.py
Po změně VERSION v docker-compose.yml uprav MC_VERSION níže a spusť znovu.
"""
import io
import json
import struct
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

MC_VERSION = "26.3"
NAZEV = "Minecraft Grussova"
SERVER_NAZEV = "Grussova"
SERVER_ADRESA = "grussova.kibos.link"
MODY = ["fabric-api", "simple-voice-chat"]

API = "https://api.modrinth.com/v2"
UA = {"User-Agent": "minecraft-server-modpack-builder"}
VYSTUP = Path(__file__).with_name("Minecraft-Grussova.mrpack")


def get_json(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA)) as r:
        return json.load(r)


def fabric_loader():
    loadery = get_json(f"https://meta.fabricmc.net/v2/versions/loader/{MC_VERSION}")
    stabilni = [l for l in loadery if l["loader"]["stable"]] or loadery
    return stabilni[0]["loader"]["version"]


def mod_soubor(slug):
    q = urllib.parse.urlencode({
        "game_versions": json.dumps([MC_VERSION]),
        "loaders": json.dumps(["fabric"]),
    })
    verze = get_json(f"{API}/project/{slug}/version?{q}")
    if not verze:
        raise SystemExit(f"{slug}: žádná verze pro {MC_VERSION}/fabric")
    v = verze[0]
    f = next((x for x in v["files"] if x["primary"]), v["files"][0])
    print(f"  {slug}: {v['version_number']} ({v['version_type']})")
    return {
        "path": f"mods/{f['filename']}",
        "hashes": {"sha1": f["hashes"]["sha1"], "sha512": f["hashes"]["sha512"]},
        "env": {"client": "required", "server": "required"},
        "downloads": [f["url"]],
        "fileSize": f["size"],
    }


def nbt_string(s):
    b = s.encode("utf-8")
    return struct.pack(">H", len(b)) + b


def servers_dat():
    """Nekomprimované NBT: {servers: [{name, ip}]} - seznam serverů ve hře."""
    server = (
        b"\x08" + nbt_string("name") + nbt_string(SERVER_NAZEV)
        + b"\x08" + nbt_string("ip") + nbt_string(SERVER_ADRESA)
        + b"\x00"
    )
    seznam = b"\x09" + nbt_string("servers") + b"\x0a" + struct.pack(">i", 1) + server
    return b"\x0a" + nbt_string("") + seznam + b"\x00"


def main():
    print(f"Sestavuji modpack pro Minecraft {MC_VERSION}")
    loader = fabric_loader()
    print(f"  fabric-loader: {loader}")
    index = {
        "formatVersion": 1,
        "game": "minecraft",
        "versionId": f"{MC_VERSION}-1",
        "name": NAZEV,
        "summary": f"Fabric + Simple Voice Chat pro server {SERVER_ADRESA}",
        "files": [mod_soubor(m) for m in MODY],
        "dependencies": {"minecraft": MC_VERSION, "fabric-loader": loader},
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("modrinth.index.json", json.dumps(index, indent=2, ensure_ascii=False))
        z.writestr("overrides/servers.dat", servers_dat())
    VYSTUP.write_bytes(buf.getvalue())
    print(f"Hotovo: {VYSTUP}")


if __name__ == "__main__":
    main()
