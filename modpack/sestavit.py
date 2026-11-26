#!/usr/bin/env python3
"""Sestaví modpack pro hráče (soubor .mrpack pro Modrinth App / Prism Launcher).

Obsahuje: Fabric loader, Fabric API, Simple Voice Chat, Traveler's Backpack, PatPat, Clapping Cat (+ povinné závislosti) a adresu serveru v seznamu serverů.
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
MODY = ["fabric-api", "simple-voice-chat", "travelersbackpack", "patpat", "clapping-cat-meme"]
# One Block (theoneblock + codxlib) běží jen na serveru, do klienta nepatří.

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


def mod_verze(slug):
    q = urllib.parse.urlencode({
        "game_versions": json.dumps([MC_VERSION]),
        "loaders": json.dumps(["fabric"]),
    })
    verze = get_json(f"{API}/project/{slug}/version?{q}")
    if not verze:
        raise SystemExit(f"{slug}: žádná verze pro {MC_VERSION}/fabric")
    return verze[0]


def mod_soubor(v, slug):
    f = next((x for x in v["files"] if x["primary"]), v["files"][0])
    print(f"  {slug}: {v['version_number']} ({v['version_type']})")
    return {
        "path": f"mods/{f['filename']}",
        "hashes": {"sha1": f["hashes"]["sha1"], "sha512": f["hashes"]["sha512"]},
        "env": {"client": "required", "server": "required"},
        "downloads": [f["url"]],
        "fileSize": f["size"],
    }


def vsechny_mody():
    """Mody z MODY plus jejich povinné závislosti (rekurzivně), každý jen jednou."""
    soubory, hotovo, fronta = [], set(), list(MODY)
    while fronta:
        slug = fronta.pop(0)
        v = mod_verze(slug)
        if v["project_id"] in hotovo:
            continue
        hotovo.add(v["project_id"])
        soubory.append(mod_soubor(v, slug))
        fronta += [d["project_id"] for d in v["dependencies"]
                   if d["dependency_type"] == "required" and d.get("project_id")]
    return soubory


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
        "versionId": f"{MC_VERSION}-3",
        "name": NAZEV,
        "summary": f"Fabric + Simple Voice Chat + Traveler's Backpack + PatPat + Clapping Cat pro server {SERVER_ADRESA}",
        "files": vsechny_mody(),
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
