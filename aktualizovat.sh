#!/bin/sh
# Aktualizace Minecraft serveru na Synology NAS (Container Manager).
#
# Co dělá:
#   1. Zeptá se registru, jestli existuje novější image (docker pull stáhne jen změněné vrstvy,
#      při stejné verzi nestáhne nic).
#   2. Když se žádný image nezměnil a docker-compose.yml (ani .env) je stejný jako při minulém
#      nasazení -> skončí, nic nerestartuje.
#   3. Když je nový image -> varuje hráče ve hře, počká, kontejnery znovu vytvoří
#      (docker compose up -d restartuje jen ty, kterých se změna týká) a smaže staré image.
#
# Plánovač úloh DSM: Ovládací panel -> Plánovač úloh -> Vytvořit -> Naplánovaná úloha -> Skript
#   definovaný uživatelem, uživatel root, příkaz:
#     sh /volume1/docker/minecraft/aktualizovat.sh
#
# Výstup jde do aktualizace.log vedle skriptu. Skript vždy končí kódem 0, takže DSM neposílá
# mail "úloha skončila neočekávaně". Chyby najdeš v logu (řádky ERROR).

DIR="/volume1/docker/minecraft"
PROJEKT="minecraft"            # stejný název jako projekt v Container Manageru
VAROVANI_S=60                  # kolik sekund předem varovat hráče před restartem
LOG="$DIR/aktualizace.log"
ZAMEK="/tmp/minecraft-aktualizace.lock"
OTISK="$DIR/.compose-otisk"    # otisk naposledy nasazeného docker-compose.yml

PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" >>"$LOG"; }
konec() { rmdir "$ZAMEK" 2>/dev/null; exit 0; }

# Log nenecháme růst donekonečna (necháme posledních 1000 řádků).
if [ -f "$LOG" ] && [ "$(wc -l <"$LOG")" -gt 2000 ]; then
  tail -n 1000 "$LOG" >"$LOG.tmp" && mv "$LOG.tmp" "$LOG"
fi

# Ochrana proti dvěma běhům najednou.
if ! mkdir "$ZAMEK" 2>/dev/null; then
  log "Jiná aktualizace ještě běží, končím."
  exit 0
fi
trap 'rmdir "$ZAMEK" 2>/dev/null' EXIT

cd "$DIR" || { log "ERROR: složka $DIR neexistuje"; konec; }

if docker compose version >/dev/null 2>&1; then
  COMPOSE="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE="docker-compose"
else
  log "ERROR: nenašel jsem docker compose (běží úloha jako root?)"
  konec
fi
COMPOSE="$COMPOSE -p $PROJEKT"

IMAGES=$($COMPOSE config --images 2>>"$LOG")
if [ -z "$IMAGES" ]; then
  log "ERROR: nepodařilo se načíst docker-compose.yml"
  konec
fi

ZMENA=""
for IMG in $IMAGES; do
  PRED=$(docker image inspect -f '{{.Id}}' "$IMG" 2>/dev/null)
  if ! docker pull -q "$IMG" >/dev/null 2>>"$LOG"; then
    log "ERROR: stažení $IMG selhalo (síť/registr), zkusím příště."
    continue
  fi
  PO=$(docker image inspect -f '{{.Id}}' "$IMG" 2>/dev/null)
  if [ "$PRED" != "$PO" ]; then
    log "Nová verze: $IMG"
    ZMENA="$ZMENA $IMG"
  fi
done

# Změna v docker-compose.yml / .env od posledního nasazení?
NOVY_OTISK=$($COMPOSE config 2>/dev/null | md5sum | cut -d' ' -f1)
if [ -n "$NOVY_OTISK" ] && [ "$NOVY_OTISK" != "$(cat "$OTISK" 2>/dev/null)" ]; then
  log "Změna v docker-compose.yml"
  ZMENA="$ZMENA docker-compose.yml"
fi

if [ -z "$ZMENA" ]; then
  log "Žádná nová verze, nic neměním."
  konec
fi

# Varování hráčům, jen když se mění image serveru (ne jen konzole) a server běží.
if echo "$ZMENA" | grep -qE 'minecraft-server|docker-compose' && docker ps -q -f name='^minecraft$' | grep -q .; then
  docker exec minecraft rcon-cli "say Server se za $VAROVANI_S s restartuje kvůli aktualizaci." >/dev/null 2>&1
  sleep "$VAROVANI_S"
  docker exec minecraft rcon-cli "save-all flush" >/dev/null 2>&1
fi

log "Nasazuji:$ZMENA"
if $COMPOSE up -d --remove-orphans >>"$LOG" 2>&1; then
  echo "$NOVY_OTISK" >"$OTISK"
  log "Hotovo."
else
  log "ERROR: docker compose up selhal, podívej se do Container Manageru."
fi

docker image prune -f >/dev/null 2>&1
konec
