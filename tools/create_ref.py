#!/usr/bin/env python3
"""Create (or move) a branch ref through the GitHub API.

Used when the commit already exists but the branch still has to be created,
for example because the git HTTPS transport is unreachable on this network.
"""
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

REPO = os.environ.get("FZMM_REPO", "HeCUana/FZMM-Mod")
BRANCH = os.environ.get("FZMM_BRANCH", "mc26.3")
SHA = os.environ.get("FZMM_COMMIT", "")
API = "https://api.github.com"
PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_token():
    out = subprocess.run(["cmd", "/c", "git credential fill < cred-in.txt"],
                         cwd=PROJECT, capture_output=True, text=True, timeout=60)
    for line in out.stdout.splitlines():
        if line.startswith("password="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("no credential")


TOKEN = get_token()


def api(method, path, payload=None, allow_404=False):
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(API + path, data=body, method=method)
    req.add_header("Authorization", "Bearer " + TOKEN)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "fzmm-port-tool")
    if body is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = resp.read()
    except urllib.error.HTTPError as e:
        if allow_404 and e.code == 404:
            return None
        raise SystemExit(f"{method} {path} -> HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:600]}")
    return json.loads(data.decode("utf-8")) if data else None


def main():
    if not SHA:
        raise SystemExit("set FZMM_COMMIT to the commit sha")
    print(f"repo   : {REPO}")
    print(f"branch : {BRANCH}")
    print(f"commit : {SHA}")

    existing = api("GET", f"/repos/{REPO}/git/refs/heads/{BRANCH}", allow_404=True)
    if existing:
        api("PATCH", f"/repos/{REPO}/git/refs/heads/{BRANCH}",
            {"sha": SHA, "force": False})
        print(f"updated {BRANCH}")
    else:
        api("POST", f"/repos/{REPO}/git/refs",
            {"ref": f"refs/heads/{BRANCH}", "sha": SHA})
        print(f"created {BRANCH}")

    check = api("GET", f"/repos/{REPO}/git/refs/heads/{BRANCH}")
    print("now at:", check["object"]["sha"])
    print(f"https://github.com/{REPO}/tree/{BRANCH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
