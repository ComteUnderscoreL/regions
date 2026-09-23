#!/usr/bin/env python3
"""Lance la récupération au démarrage, puis toutes les heures ; commit/push si nécessaire."""
import argparse
from datetime import datetime, timezone
import math
import os
from pathlib import Path
import subprocess
import sys
import time

from scrape_scores import FileLock, ScoreError, ROOT, log

SCORE_PATH = "data/player_scores.tsv"
COMMIT_PREFIX = "auto(scores): "


def run(repo, command, timeout=180, allowed=(0,)):
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GCM_INTERACTIVE"] = "never"
    env.setdefault("GIT_SSH_COMMAND", "ssh -oBatchMode=yes")
    result = subprocess.run(command, cwd=repo, env=env, capture_output=True, text=True,
                            encoding="utf-8", errors="replace", timeout=timeout)
    if result.returncode not in allowed:
        details = "\n".join(part.strip() for part in (result.stdout, result.stderr) if part.strip())
        raise ScoreError("Commande échouée : " + " ".join(command[:3]) + "\n" + details)
    return result


def git(repo, *args, allowed=(0,)):
    return run(repo, ["git", *args], allowed=allowed)


def verify_pending_commits(repo, remote_head):
    commits = git(repo, "rev-list", remote_head + "..HEAD").stdout.split()
    for commit in commits:
        subject = git(repo, "show", "-s", "--format=%s", commit).stdout.strip()
        parents = git(repo, "show", "-s", "--format=%P", commit).stdout.split()
        paths = git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", commit).stdout.splitlines()
        if len(parents) != 1 or not subject.startswith(COMMIT_PREFIX) or set(paths) != {SCORE_PATH}:
            raise ScoreError("Commits locaux personnels non publiés : les pousser/résoudre manuellement avant de lancer la boucle.")
    return bool(commits)


def cycle(repo, remote="origin", branch="main"):
    if Path(git(repo, "rev-parse", "--show-toplevel").stdout.strip()).resolve() != repo:
        raise ScoreError("--repo doit désigner la racine du dépôt.")
    if git(repo, "branch", "--show-current").stdout.strip() != branch:
        raise ScoreError("La branche courante doit être " + branch + ". Aucun changement de branche automatique.")
    if git(repo, "status", "--porcelain", "--untracked-files=no").stdout.strip():
        raise ScoreError("Des fichiers suivis sont modifiés ou indexés. Les committer/ranger avant le cycle automatique.")
    # Refuse un fichier de scores non suivi préexistant : il doit être vérifié et ajouté manuellement.
    tracked = git(repo, "ls-files", "--error-unmatch", "--", SCORE_PATH, allowed=(0, 1)).returncode == 0
    if (repo / SCORE_PATH).exists() and not tracked:
        raise ScoreError("Le TSV existe sans être suivi par Git. Le vérifier et le committer d'abord.")
    git(repo, "fetch", "--no-tags", remote, branch)
    remote_head = git(repo, "rev-parse", "FETCH_HEAD").stdout.strip()
    ahead = verify_pending_commits(repo, remote_head)
    if ahead:
        if git(repo, "merge-base", "--is-ancestor", remote_head, "HEAD", allowed=(0, 1)).returncode:
            raise ScoreError("Historique Git divergent : réconcilier manuellement, aucun push forcé.")
        # Réessaie un push précédemment refusé, même s'il n'y a aucun nouveau score.
        git(repo, "push", remote, "HEAD:refs/heads/" + branch)
        log("[PUSH] Scores précédemment en attente publiés.")
    else:
        git(repo, "merge", "--ff-only", remote_head)
    for setting in ("user.name", "user.email"):
        if not git(repo, "config", "--get", setting, allowed=(0, 1)).stdout.strip():
            raise ScoreError("Configurer git " + setting + " avant de lancer la boucle.")
    # Appelle réellement le premier script, avec le même interpréteur Python.
    result = run(repo, [sys.executable, str(repo / "scrape_scores.py")], timeout=3600)
    if result.stdout:
        log(result.stdout.rstrip())
    if result.stderr:
        log(result.stderr.rstrip())
    # Vérifie à nouveau qu'aucune modification personnelle n'est apparue pendant le réseau.
    staged = git(repo, "diff", "--cached", "--name-only", "-z").stdout
    changed = set(filter(None, git(repo, "diff", "--name-only", "-z").stdout.split("\0")))
    if staged or changed - {SCORE_PATH}:
        raise ScoreError("D'autres modifications sont apparues pendant le cycle ; aucun commit automatique.")
    if SCORE_PATH not in changed and (tracked or not (repo / SCORE_PATH).exists()):
        log("[OK] Aucun changement à pousser.")
        return
    git(repo, "add", "--", SCORE_PATH)
    if git(repo, "diff", "--cached", "--quiet", "--", SCORE_PATH, allowed=(0, 1)).returncode == 0:
        log("[OK] Aucun changement à pousser.")
        return
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    git(repo, "commit", "--only", "-m", COMMIT_PREFIX + stamp, "--", SCORE_PATH)
    git(repo, "push", remote, "HEAD:refs/heads/" + branch)
    log("[PUSH] Scores mis à jour.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--interval", type=float, default=3600, help="Intervalle entre débuts de cycles, en secondes.")
    parser.add_argument("--once", action="store_true", help="Un seul cycle, puis quitter.")
    args = parser.parse_args(argv)
    args.repo = args.repo.resolve()
    if not math.isfinite(args.interval) or args.interval <= 0 or not args.remote or args.remote.startswith("-") or not args.branch or args.branch.startswith("-"):
        parser.error("Intervalle, remote ou branche invalide.")
    try:
        with FileLock(args.repo / "auto-update-scores"):
            while True:
                started = time.monotonic()
                log("[CYCLE] " + datetime.now(timezone.utc).isoformat(timespec="seconds"))
                status = 0
                try:
                    cycle(args.repo, args.remote, args.branch)
                except (ScoreError, OSError, subprocess.TimeoutExpired) as exc:
                    print("[ERREUR] " + str(exc), file=sys.stderr, flush=True)
                    status = 1
                if args.once:
                    return status
                elapsed = time.monotonic() - started
                # Pas de rattrapage en rafale si un cycle dépasse une heure.
                delay = args.interval - elapsed if elapsed < args.interval else args.interval
                log("[ATTENTE] Prochain cycle dans " + str(round(delay)) + " secondes.")
                time.sleep(delay)
    except KeyboardInterrupt:
        log("[ARRÊT] Boucle arrêtée.")
        return 0
    except (ScoreError, OSError) as exc:
        print("[ERREUR] " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
