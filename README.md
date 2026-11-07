# Minecraft Java server 26.3 (Fabric + voice chat) na Synology NAS

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

## Voice chat (Simple Voice Chat)
Server běží na **Fabricu** (vanilla hra s podporou modů) a při startu si sám stáhne z Modrinthu
`fabric-api` a `simple-voice-chat` do `data\mods`. Hlas jde přes port **24454/UDP**.

**Na serveru (jednou):**
1. Container Manager -> Projekt -> `minecraft` -> **Zastavit**, pak **Akce -> Sestavit** (načte nový compose).
2. V logu musí být `Voice chat server started at port 24454`.
3. Firewall DSM: povol port **24454/UDP** (Ovládací panel -> Zabezpečení -> Brána firewall).
4. Hraní z internetu: na routeru přesměruj kromě 25565/TCP i **24454/UDP** na 192.168.10.11.

**Každý hráč (na svém PC):**
1. Stáhni a spusť instalátor Fabricu z https://fabricmc.net/use/installer/ -> Client -> verze **26.3** -> Install.
2. Z Modrinthu stáhni pro 26.3 / Fabric:
   - Fabric API: https://modrinth.com/mod/fabric-api
   - Simple Voice Chat: https://modrinth.com/plugin/simple-voice-chat
3. Oba `.jar` soubory dej do `%appdata%\.minecraft\mods` (složku případně vytvoř).
4. V launcheru vyber profil **fabric-loader-26.3** a spusť hru.
   Jednodušší alternativa: launcher Modrinth App nebo Prism Launcher, kde mody přidáš kliknutím.
5. Ve hře klávesa **V** otevře nastavení hlasu (mikrofon, hlasitost), výchozí je hlasová aktivace,
   push-to-talk je na klávese **Caps Lock** (lze přenastavit). Klávesa **G** = skupiny.

**Doména přes Cloudflare + MikroTik:** záznam pro hru (CNAME na MikroTik DDNS) musí být **DNS only (šedý mráček)**,
Cloudflare proxy UDP nepropustí. Klient posílá hlas na stejnou doménu jako hru, jen na port 24454, takže `voice_host`
nastavovat netřeba. Na MikroTiku přidej přesměrování (rozhraní WAN uprav podle sebe):
```
/ip firewall nat add chain=dstnat in-interface-list=WAN protocol=udp dst-port=24454 action=dst-nat to-addresses=192.168.10.11 to-ports=24454 comment="Minecraft voice chat"
```

Hráč bez modu se na server připojí normálně, jen neslyší a nemluví.
Konfigurace serverové části: `data\config\voicechat\voicechat-server.properties` (vzdálenost hlasu, port…).

**Update Minecraftu s mody:** před změnou `VERSION` ověř na Modrinthu, že `simple-voice-chat` a `fabric-api`
už mají verzi pro novou verzi hry, jinak server nenajde soubor a nenastartuje. Hráči pak aktualizují mody i u sebe.

**Návrat na čistý vanilla:** vrať `TYPE: "VANILLA"` a smaž řádky `MODRINTH_*`. Svět zůstane.

## Nastavení serveru (server.properties)
Otevři `\\192.168.10.11\docker\minecraft\data\server.properties` v Poznámkovém bloku,
uprav (MOTD, obtížnost, max hráčů, seed…) a v konzoli zadej `stop` pro restart.
Logy jsou v `data\logs`, svět v `data\world`.

## Konzole hlásí „server není dostupný“
1. Podívej se do logu kontejneru `minecraft`. První start stahuje server a generuje svět, trvá to několik minut. Konzole se připojí až po hlášce `Done` a `RCON running on 0.0.0.0:25575`.
2. V `data\server.properties` musí být `enable-rcon=true`, `rcon.port=25575` a `rcon.password` stejné jako `RCON_PASSWORD` v `.env`.
3. Po změně `.env` nebo `docker-compose.yml` projekt v Container Manageru zastav a znovu **Sestav**, aby se změny projevily.
4. Pokud konzole hlásí `RconServer [mc:25575]: Connection timed out` nebo log `EAI_AGAIN` / `UnknownHostException`, blokuje firewall DSM provoz kontejnerů (síť Dockeru 172.16.0.0/12). V Ovládací panel -> Zabezpečení -> Brána firewall -> Upravit pravidla přidej pravidlo: Porty **Vše**, Zdrojová IP **Podsíť 172.16.0.0 / 255.240.0.0**, Akce **Povolit**, a posuň ho nahoru nad pravidla „Odepřít“.
5. Pokud log hlásí `EAI_AGAIN` nebo `UnknownHostException`, kontejnery nemají DNS. V compose je proto nastavené `dns: 1.1.1.1, 8.8.8.8`; zkontroluj i DNS v Ovládací panel -> Síť.
6. Pokud server v logu padá na `Permission denied` nad `/data`, nesedí `UID`/`GID` (viz níže).

## UID / GID (práva k souborům)
Aby šly soubory v `data` upravovat přes síťovou složku, server musí běžet pod tvým uživatelem.
Přes SSH na NASu zadej `id tvuj_uzivatel` a čísla `uid` a `gid` dej do `UID` a `GID`.
Výchozí 1026/100 sedí na prvního vytvořeného uživatele.

## Firewall a přístup z internetu
- Pokud máš zapnutý firewall DSM, povol porty 25565 (hra), 24454/UDP (voice chat) a 4326–4327 (konzole) pro místní síť a navíc vše ze zdrojové podsítě Dockeru 172.16.0.0/255.240.0.0 (jinak se kontejnery nespojí mezi sebou ani s internetem).
- Pro hraní z internetu přesměruj na routeru jen port **25565/TCP** a **24454/UDP** (voice chat) na 192.168.10.11.
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
