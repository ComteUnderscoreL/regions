#!/usr/bin/env python3
"""Récupère les scores des challenges liés aux régions visible:true (Python 3.9+)."""
import argparse
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler

ROOT = Path(__file__).resolve().parent
FIELDS = ["player_id", "player", "region_id", "challenge_id", "score", "time_seconds", "date"]
API = "https://www.geoguessr.com/api/v3/results/highscores/"
ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")


class ScoreError(Exception):
    pass


def log(message):
    print(message, flush=True)


class FileLock:
    """Verrou OS libéré même si le processus s'arrête brutalement."""
    def __init__(self, target):
        digest = hashlib.sha256(str(Path(target).resolve()).encode()).hexdigest()
        self.path = Path(tempfile.gettempdir()) / ("regions-scores-" + digest + ".lock")
        self.file = None

    def __enter__(self):
        self.file = self.path.open("a+b")
        try:
            if os.name == "nt":
                import msvcrt
                self.file.seek(0, 2)
                if self.file.tell() == 0:
                    self.file.write(b"0")
                    self.file.flush()
                self.file.seek(0)
                msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self.file.close()
            raise ScoreError("Une autre récupération utilise déjà ce dépôt/fichier.") from exc
        return self

    def __exit__(self, *args):
        if os.name == "nt":
            import msvcrt
            self.file.seek(0)
            msvcrt.locking(self.file.fileno(), msvcrt.LK_UNLCK, 1)
        self.file.close()


def challenge_token(value):
    if not isinstance(value, str):
        raise ScoreError("challenge_url doit être une chaîne de caractères.")
    value = value.strip()
    if ID_RE.fullmatch(value):
        return value
    try:
        parsed = urlparse(value)
    except ValueError:
        raise ScoreError("Lien de challenge invalide : URL mal formée.") from None
    if parsed.scheme == "https" and parsed.netloc.lower() in ("www.geoguessr.com", "geoguessr.com"):
        parts = parsed.path.strip("/").split("/")
        # Les liens partagés peuvent commencer par une langue, par exemple /fr/.
        if parts and re.fullmatch(r"[a-z]{2}(?:-[A-Za-z]{2})?", parts[0]):
            parts = parts[1:]
        if len(parts) == 2 and parts[0] == "challenge" and ID_RE.fullmatch(parts[1]):
            return parts[1]
        # GeoGuessr partage aussi /fr/maps/<map>/play?challengeId=<challenge>.
        # Seul l'identifiant du challenge est utilisé pour appeler l'API fixe.
        if (len(parts) == 3 and parts[0] == "maps" and ID_RE.fullmatch(parts[1])
                and parts[2] == "play"):
            tokens = parse_qs(parsed.query, keep_blank_values=True).get("challengeId", [])
            if len(tokens) == 1 and ID_RE.fullmatch(tokens[0]):
                return tokens[0]
    raise ScoreError("Lien de challenge invalide : une URL GeoGuessr /challenge/<id>, "
                     "/maps/<map>/play?challengeId=<id> (avec ou sans /fr/) "
                     "ou un identifiant est attendu.")


def selected_regions(config):
    regions = config.get("regions") if isinstance(config, dict) else None
    if not isinstance(regions, list):
        raise ScoreError("Configuration invalide : liste regions absente.")
    selected, seen = [], set()
    for region in regions:
        if not isinstance(region, dict):
            raise ScoreError("Entrée de région invalide.")
        if region.get("visible") is not True:
            continue
        region_id = region.get("id", "")
        if not isinstance(region_id, str) or not ID_RE.fullmatch(region_id):
            raise ScoreError("Une région visible a un identifiant invalide.")
        if region_id in seen:
            raise ScoreError("Région visible en double : " + region_id)
        seen.add(region_id)
        url = region.get("challenge_url", "")
        if not url or (isinstance(url, str) and not url.strip()):
            log("[IGNORÉ] " + region_id + " : aucun challenge renseigné.")
            continue
        try:
            token = challenge_token(url)
        except ScoreError as exc:
            raise ScoreError("Région " + region_id + " : " + str(exc)) from None
        selected.append((region_id, token))
    return selected


def cookie_from_env():
    cookie_file = os.environ.get("GEOGUESSR_COOKIE_FILE")
    cookie = (Path(cookie_file).expanduser().read_text(encoding="utf-8").strip()
              if cookie_file else os.environ.get("COOKIE_LINE", "").strip())
    if "\n" in cookie or "\r" in cookie:
        raise ScoreError("Le cookie doit tenir sur une seule ligne.")
    return cookie


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Ne jamais transmettre un cookie à une page de connexion ou un autre domaine.
        return None


class GeoGuessrClient:
    def __init__(self, cookie="", timeout=30, delay=1.0, retries=3):
        self.cookie, self.timeout, self.delay, self.retries = cookie, timeout, delay, retries
        self.opener = build_opener(NoRedirect())
        self.last_request = 0.0

    def get_page(self, token, pagination_token=None):
        params = {"friends": "false"}
        if pagination_token:
            params["paginationToken"] = pagination_token
        url = API + token + "?" + urlencode(params)
        headers = {"Accept": "application/json", "User-Agent": "regions-scores/1.0"}
        if self.cookie:
            headers["Cookie"] = self.cookie
        for attempt in range(self.retries + 1):
            wait = self.delay - (time.monotonic() - self.last_request)
            if wait > 0:
                time.sleep(wait)
            self.last_request = time.monotonic()
            try:
                with self.opener.open(Request(url, headers=headers), timeout=self.timeout) as response:
                    payload = response.read()
                try:
                    data = json.loads(payload)
                except (ValueError, UnicodeDecodeError) as exc:
                    raise ScoreError("Réponse non JSON pour " + token + " (connexion/accès à vérifier).") from exc
                if not isinstance(data, dict) or not isinstance(data.get("items"), list):
                    raise ScoreError("Réponse inattendue pour " + token + " : liste items absente.")
                return data
            except HTTPError as exc:
                status = exc.code
                retry_after = exc.headers.get("Retry-After", "")
                exc.close()
                if status in (401, 403):
                    raise ScoreError("GeoGuessr HTTP %s : accès refusé ; vérifier la session COOKIE_LINE/"
                                     "GEOGUESSR_COOKIE_FILE et l'accès au challenge %s." % (status, token)) from None
                if status == 404:
                    raise ScoreError("Challenge " + token + " : HTTP 404, scores non accessibles. "
                                     "Aucun score existant ne sera effacé.") from None
                if status not in (429, 500, 502, 503, 504) or attempt == self.retries:
                    raise ScoreError("GeoGuessr HTTP %s pour %s." % (status, token)) from None
                pause = min(60, max(2 ** (attempt + 1), int(retry_after) if retry_after.isdigit() else 0))
            except (URLError, TimeoutError, OSError):
                if attempt == self.retries:
                    raise ScoreError("Échec réseau pour le challenge " + token + ".") from None
                pause = 2 ** (attempt + 1)
            log("[RETRY] " + token + " dans " + str(pause) + " secondes.")
            time.sleep(pause)


def all_items(client, token, max_pages=10000):
    items, cursor, seen_cursors = [], None, set()
    for _ in range(max_pages):
        page = client.get_page(token, cursor)
        batch = page["items"]
        if any(not isinstance(item, dict) for item in batch):
            raise ScoreError("Résultat mal formé pour " + token)
        items.extend(batch)
        cursor = page.get("paginationToken")
        if cursor in (None, ""):
            return items
        if not isinstance(cursor, str) or cursor in seen_cursors or not batch:
            raise ScoreError("Pagination incohérente pour " + token + " ; récupération annulée.")
        seen_cursors.add(cursor)
    raise ScoreError("Limite de pagination atteinte ; récupération annulée.")


def number(value, label, integer=False):
    if isinstance(value, bool) or value is None:
        raise ScoreError(label + " absent ou invalide.")
    try:
        result = float(value)
    except (ValueError, TypeError):
        raise ScoreError(label + " invalide.") from None
    if not math.isfinite(result) or result < 0 or (integer and not result.is_integer()):
        raise ScoreError(label + " invalide.")
    return int(result) if integer else result


def text(value):
    return " ".join(str(value).split())


def parse_item(item, region_id, token):
    game = item.get("game")
    player = game.get("player") if isinstance(game, dict) else None
    if not isinstance(player, dict):
        raise ScoreError("Résultat sans game.player pour " + token)
    state = game.get("state")
    if isinstance(state, str) and state.lower() in ("started", "inprogress", "in_progress"):
        return None
    guesses, rounds = player.get("guesses"), game.get("rounds")
    if isinstance(guesses, list) and isinstance(rounds, list) and rounds and len(guesses) < len(rounds):
        return None
    player_id = player.get("id") or item.get("userId")
    if not isinstance(player_id, str) or not ID_RE.fullmatch(player_id):
        raise ScoreError("Identifiant joueur absent ou invalide pour " + token)
    raw_score = player.get("totalScore")
    if isinstance(raw_score, dict):
        raw_score = raw_score.get("amount")
    if raw_score is None:
        raw_score = item.get("totalScore")
    score = number(raw_score, "Score", integer=True)
    if score > 25000:
        raise ScoreError("Score supérieur à 25 000 pour " + token)
    raw_time = player.get("totalTime")
    if isinstance(guesses, list) and any(not isinstance(guess, dict) for guess in guesses):
        raise ScoreError("Liste de manches mal formée pour " + token)
    if raw_time is None and isinstance(guesses, list) and guesses and all(guess.get("time") is not None for guess in guesses):
        raw_time = sum(number(guess.get("time"), "Temps d'une manche") for guess in guesses)
    # Un temps inconnu reste vide : il ne doit jamais attribuer une médaille de vitesse.
    seconds = "" if raw_time is None else format(number(raw_time, "Temps total"), ".12g")
    nickname = text(player.get("nick") or item.get("playerName") or player_id)
    date = ""
    for field in ("completedAt", "finishedAt"):
        value = game.get(field)
        if isinstance(value, str):
            try:
                date = datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()
                break
            except ValueError:
                pass
    return dict(zip(FIELDS, [player_id, nickname, region_id, token, str(score), seconds, date]))


def key(row):
    return row["region_id"], row["challenge_id"], row["player_id"]


def read_scores(path):
    if not path.exists():
        return {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames != FIELDS:
            raise ScoreError("En-tête TSV inattendu : " + str(path))
        rows = {}
        for row in reader:
            if set(row) != set(FIELDS) or any(v is None for v in row.values()):
                raise ScoreError("Ligne TSV mal formée : " + str(path))
            if key(row) in rows:
                if row != rows[key(row)]:
                    raise ScoreError("Doublon contradictoire dans le TSV existant : " + str(key(row)))
            rows[key(row)] = row
        return rows


def serialize(rows):
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    for row in sorted(rows.values(), key=key):
        writer.writerow(row)
    return buffer.getvalue().encode("utf-8")


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix="." + path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if path.exists():
            os.chmod(temporary, path.stat().st_mode & 0o777)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def collect(config_path, output_path, client, dry_run=False):
    selected = selected_regions(json.loads(config_path.read_text(encoding="utf-8-sig")))
    if not selected:
        log("[OK] Aucun challenge actif : fichier inchangé.")
        return False
    old = read_scores(output_path)
    updates, cache, refreshed, failed = {}, {}, set(), []
    today = datetime.now(timezone.utc).date().isoformat()
    for region_id, token in selected:
        try:
            if token not in cache:
                try:
                    cache[token] = all_items(client, token)
                except ScoreError as exc:
                    cache[token] = exc
            if isinstance(cache[token], ScoreError):
                raise cache[token]
            # N'ajoute aucun résultat de ce challenge avant validation complète.
            region_rows = {}
            for item in cache[token]:
                row = parse_item(item, region_id, token)
                if row is None:
                    continue
                previous = old.get(key(row), {})
                row["date"] = row["date"] or previous.get("date") or today
                if not row["time_seconds"] and previous.get("score") == row["score"]:
                    row["time_seconds"] = previous.get("time_seconds", "")
                if key(row) in region_rows and row != region_rows[key(row)]:
                    raise ScoreError("Le classement a changé pendant la pagination de " + token + ". Réessayer.")
                region_rows[key(row)] = row
        except ScoreError as exc:
            failed.append(region_id)
            log("[AVERTISSEMENT] " + region_id + " (" + token + ") : " + str(exc)
                + " Anciens scores conservés pour ce challenge ; poursuite des autres régions.")
            continue
        old_keys = {k for k in old if k[:2] == (region_id, token)}
        removed = len(old_keys - region_rows.keys())
        updates.update(region_rows)
        refreshed.add((region_id, token))
        log("[OK] " + region_id + " : " + str(len(region_rows)) + " résultat(s) terminé(s)"
            + (", " + str(removed) + " ancien(s) résultat(s) retiré(s)" if removed else "") + ".")
    if failed:
        log("[BILAN] " + str(len(refreshed)) + " challenge(s) actualisé(s), "
            + str(len(failed)) + " conservé(s) après erreur.")
    if not refreshed:
        raise ScoreError("Aucun challenge n'a pu être récupéré. Fichier existant conservé.")
    # Remplace uniquement les challenges entièrement validés, y compris ceux vides.
    # Les challenges en erreur, anciens challenges et régions masquées sont conservés.
    merged = {k: row for k, row in old.items() if k[:2] not in refreshed}
    merged.update(updates)
    data = serialize(merged)
    if output_path.exists() and output_path.read_bytes() == data:
        log("[OK] Scores inchangés.")
        return False
    if not dry_run:
        atomic_write(output_path, data)
    log(("[SIMULATION] " if dry_run else "[ÉCRIT] ") + str(output_path) + " : " + str(len(merged)) + " lignes.")
    return True


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "data/regions.json")
    parser.add_argument("--output", type=Path, default=ROOT / "data/player_scores.tsv")
    parser.add_argument("--list", action="store_true", help="Lister les challenges actifs sans connexion réseau.")
    parser.add_argument("--dry-run", action="store_true", help="Récupérer et vérifier sans écrire.")
    parser.add_argument("--timeout", type=float, default=30)
    parser.add_argument("--delay", type=float, default=1.0, help="Délai minimal entre requêtes, en secondes.")
    args = parser.parse_args(argv)
    try:
        if not math.isfinite(args.timeout) or not math.isfinite(args.delay) or args.timeout <= 0 or args.delay < 0:
            raise ScoreError("timeout doit être positif et delay non négatif.")
        if args.list:
            for region, token in selected_regions(json.loads(args.config.read_text(encoding="utf-8-sig"))):
                log(region + "\t" + token)
        else:
            with FileLock(args.output):
                collect(args.config, args.output, GeoGuessrClient(cookie_from_env(), args.timeout, args.delay), args.dry_run)
    except (ScoreError, OSError, ValueError) as exc:
        print("[ERREUR] " + str(exc) + " Aucun fichier partiel n'est publié.", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
