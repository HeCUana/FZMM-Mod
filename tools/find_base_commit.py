#!/usr/bin/env python3
"""
Compare the locally staged tree against the recent upstream commits and report
how many files match, so the port can be based on the closest ancestor.

Blob SHAs are content addressed and identical between the local index and
GitHub, so this is an exact comparison.
"""
import json
import os
import subprocess
import sys
import urllib.request

REPO = os.environ.get("FZMM_REPO", "HeCUana/FZMM-Mod")
BRANCH = os.environ.get("FZMM_BRANCH", "dev")
API = "https://api.github.com"
PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CRED_FILE = os.path.join(PROJECT, "cred-in.txt")


def get_token():
    out = subprocess.run(["cmd", "/c", "git credential fill < cred-in.txt"],
                         cwd=PROJECT, capture_output=True, text=True, timeout=60)
    for line in out.stdout.splitlines():
        if line.startswith("password="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("no credential")


TOKEN = get_token()


def api(method, path):
    req = urllib.request.Request(API + path, method=method)
    req.add_header("Authorization", "Bearer " + TOKEN)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "fzmm-port-tool")
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def local_index():
    out = subprocess.run(["git", "ls-files", "-s", "-z"], cwd=PROJECT,
                         capture_output=True, text=True, timeout=120)
    result = {}
    for entry in out.stdout.split("\0"):
        if not entry.strip():
            continue
        meta, path = entry.split("\t", 1)
        _mode, sha, _stage = meta.split()
        result[path.replace("\\", "/")] = sha
    return result


def main():
    local = local_index()
    print(f"local staged files: {len(local)}\n")

    commits = api("GET", f"/repos/{REPO}/commits?sha={BRANCH}&per_page=12")
    best = None
    for c in commits:
        tree = api("GET", f"/repos/{REPO}/git/trees/{c['sha']}?recursive=1")
        remote = {e["path"]: e["sha"] for e in tree["tree"] if e["type"] == "blob"}
        same = sum(1 for p, s in local.items() if remote.get(p) == s)
        only_local = [p for p in local if p not in remote]
        only_remote = [p for p in remote if p not in local]
        diff = len(local) - same
        title = c["commit"]["message"].split("\n")[0]
        print(f"{c['sha'][:9]}  match {same:4d}/{len(local)}  diff {diff:4d}  "
              f"+local {len(only_local):3d}  -remote {len(only_remote):3d}  {title[:52]}")
        score = same
        if best is None or score > best[0]:
            best = (score, c["sha"], title, only_local, only_remote, diff)
    print()
    print(f"best base: {best[1][:9]}  ({best[0]} matching files)  {best[2][:60]}")
    print()
    print(f"--- files only in the local tree ({len(best[3])}) ---")
    for p in sorted(best[3]):
        print("   +", p)
    print()
    print(f"--- files only in the upstream base ({len(best[4])}) ---")
    for p in sorted(best[4]):
        print("   -", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
