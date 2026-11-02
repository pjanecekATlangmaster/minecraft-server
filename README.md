# Minecraft Java server 26.3 na Synology NAS

## Instalace
1. V DSM nainstaluj **Container Manager** (Centrum balíčků). Potřebuješ NAS s procesorem x86_64 (Intel/AMD) a ideálně 8 GB RAM.
2. Ve sdílené složce `\\192.168.10.11\docker\minecraft\` vytvoř podsložky `data` a `konzole-db`.
3. Do `\\192.168.10.11\docker\minecraft\` nakopíruj `docker-compose.yml` a `.env.example`.
4. Zkopíruj `.env.example` jako `.env` a vyplň v něm hesla (soubor `.env` se do gitu neukládá).
   Případně uprav v `docker-compose.yml` `UID`/`GID` (viz níže) a `MEMORY`.
5. Container Manager -> **Projekt** -> **Vytvořit**:
   - Název: `minecraft`
   - Cesta: `/docker/minecraft`
   - Zdroj: **Použít existující docker-compose.yml**
   - Dokončit. První start stahuje image a server, chvíli to trvá.
6. Log: Container Manager -> Kontejner -> `minecraft` -> Podrobnosti -> Protokol (čekej na `Done`).
7. Ve hře se připoj na `192.168.10.11:25565`.

## Webová konzole
`http://192.168.10.11:4326`, přihlášení `admin` + heslo `WEB_PASSWORD` z `.env`.

Užitečné příkazy:
- `whitelist on`, `whitelist add Nick`, `whitelist remove Nick`
- `op Nick`, `deop Nick`
- `difficulty hard`, `gamerule keepInventory true`, `time set day`
- `save-all`, `stop` (server se díky `restart: unless-stopped` znovu spustí = restart)

## Nastavení serveru (server.properties)
Otevři `\\192.168.10.11\docker\minecraft\data\server.properties` v Poznámkovém bloku,
uprav (MOTD, obtížnost, max hráčů, seed…) a v konzoli zadej `stop` pro restart.
Logy jsou v `data\logs`, svět v `data\world`.

## Konzole hlásí „server není dostupný“
1. Restartuj kontejner `minecraft-konzole`. Konzole se k serveru připojuje jen při svém startu, takže když nastartovala dřív než server, sama se nepřipojí.
1. Podívej se do logu kontejneru `minecraft`. První start stahuje server a generuje svět, trvá to několik minut. Konzole se připojí až po hlášce `Done` a `RCON running on 0.0.0.0:25575`.
2. V `data\server.properties` musí být `enable-rcon=true`, `rcon.port=25575` a `rcon.password` stejné jako `RCON_PASSWORD` v `.env`.
3. Po změně `.env` nebo `docker-compose.yml` projekt v Container Manageru zastav a znovu **Sestav**, aby se změny projevily.
4. Pokud log hlásí `EAI_AGAIN` nebo `UnknownHostException`, kontejnery nemají DNS. V compose je proto nastavené `dns: 1.1.1.1, 8.8.8.8`; zkontroluj i DNS v Ovládací panel -> Síť.
5. Pokud server v logu padá na `Permission denied` nad `/data`, nesedí `UID`/`GID` (viz níže).

## UID / GID (práva k souborům)
Aby šly soubory v `data` upravovat přes síťovou složku, server musí běžet pod tvým uživatelem.
Přes SSH na NASu zadej `id tvuj_uzivatel` a čísla `uid` a `gid` dej do `UID` a `GID`.
Výchozí 1026/100 sedí na prvního vytvořeného uživatele.

## Firewall a přístup z internetu
- Pokud máš zapnutý firewall DSM, povol porty 25565 (hra) a 4326–4327 (konzole) pro místní síť.
- Pro hraní z internetu přesměruj na routeru jen port **25565/TCP** na 192.168.10.11.
  Porty konzole (4326, 4327) do internetu nevystavuj.

## Update
Image serveru se stahuje z GitHub Container Registry: `ghcr.io/itzg/minecraft-server:java25`.
Tag `java25` je „plovoucí“: autor do něj průběžně vydává opravy, takže stačí image znovu stáhnout.

**Nová verze Minecraftu (např. 26.4):**
1. Zálohuj složku `data` (zkopíruj na PC, Hyper Backup nebo snapshot).
2. V `docker-compose.yml` změň `VERSION: "26.3"` na `"26.4"`.
3. Container Manager -> Projekt -> `minecraft` -> **Zastavit**, pak **Akce -> Sestavit**.
   Server si při startu stáhne nový server.jar od Mojangu.

**Aktualizace samotného image (opravy, nová Java):**
- Container Manager -> **Image** -> u `ghcr.io/itzg/minecraft-server` se objeví **Aktualizace k dispozici** -> klikni.
- Nebo přes SSH: `cd /volume1/docker/minecraft && sudo docker compose pull && sudo docker compose up -d`

Kdyby budoucí verze Minecraftu vyžadovala novější Javu, změň tag image (např. `java25` -> `java26`) a sestav projekt znovu.

## Proč „nacházím jen starší verze“
Image `itzg/minecraft-server` nemá verzi v názvu tagu. Verzi určuje proměnná `VERSION`
a server.jar se stahuje přímo od Mojangu, takže funguje i pro 26.x. Nutná je jen Java 25 (tag `java25`).
