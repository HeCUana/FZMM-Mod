#!/usr/bin/env python3
"""
Push the working tree to a GitHub branch through the Git Data API.

github.com:443 is unreachable from this network (the HTTPS git protocol times
out), but api.github.com works. So instead of `git push` this script:

  1. reads the base commit / tree through the API
  2. compares the base tree with the locally staged files (`git ls-files -s`)
  3. uploads only the changed blobs
  4. creates a tree based on the base tree
  5. creates a commit whose parent is the base commit
  6. creates or moves the target ref

The upstream history is preserved: the new commit's parent is the base commit,
so from GitHub's point of view this is a normal fast-forward.

The credential is read through `git credential fill`, so the token never has to
appear in a command line or in the transcript.

Environment variables:
  FZMM_REPO    target repository          (default HeCUana/FZMM-Mod)
  FZMM_BASE    base commit sha           (default: the upstream 26.2/dev head)
  FZMM_BRANCH  branch to create / update (default mc26.3)
  FZMM_MSG     commit message
"""
import base64
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

REPO = os.environ.get("FZMM_REPO", "HeCUana/FZMM-Mod")
BRANCH = os.environ.get("FZMM_BRANCH", "mc26.3")
BASE = os.environ.get("FZMM_BASE", "5956e22eaed95af9681741fde31df7d0ce2f1a49")
API = "https://api.github.com"
PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_token():
    out = subprocess.run(
        ["cmd", "/c", "git credential fill < cred-in.txt"],
        cwd=PROJECT, capture_output=True, text=True, timeout=60,
    )
    for line in out.stdout.splitlines():
        if line.startswith("password="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("could not read the GitHub credential from the credential manager")


TOKEN = get_token()


def api(method, path, payload=None):
    url = path if path.startswith("http") else API + path
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Authorization", "Bearer " + TOKEN)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "fzmm-port-tool")
    if body is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = resp.read()
    except urllib.error.HTTPError as e:
        raise SystemExit(f"{method} {path} -> HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:900]}")
    return json.loads(data.decode("utf-8")) if data else None


def local_index():
    """path -> (mode, blob sha) for every file staged in the local repository."""
    out = subprocess.run(["git", "ls-files", "-s", "-z"], cwd=PROJECT,
                         capture_output=True, text=True, timeout=180)
    if out.returncode != 0:
        raise SystemExit("git ls-files failed: " + out.stderr)
    result = {}
    for entry in out.stdout.split("\0"):
        if not entry.strip():
            continue
        meta, path = entry.split("\t", 1)
        mode, sha, _stage = meta.split()
        result[path.replace("\\", "/")] = (mode, sha)
    return result


def main():
    print(f"repo  : {REPO}")
    print(f"branch: {BRANCH}")
    print(f"base  : {BASE}")

    base_commit = api("GET", f"/repos/{REPO}/git/commits/{BASE}")
    base_tree = base_commit["tree"]["sha"]
    print(f"base tree: {base_tree}")

    remote = api("GET", f"/repos/{REPO}/git/trees/{base_tree}?recursive=1")
    remote_files = {e["path"]: e["sha"] for e in remote["tree"] if e["type"] == "blob"}

    local = local_index()
    print(f"base blobs: {len(remote_files)}   local files: {len(local)}")

    changed = [p for p, (_m, sha) in local.items() if remote_files.get(p) != sha]
    deleted = [p for p in remote_files if p not in local]
    print(f"changed/new: {len(changed)}   deleted: {len(deleted)}")
    for p in deleted:
        print(f"  D {p}")

    entries = []
    for path in changed:
        mode, sha = local[path]
        with open(os.path.join(PROJECT, path.replace("/", os.sep)), "rb") as fh:
            data = fh.read()
        blob = api("POST", f"/repos/{REPO}/git/blobs",
                   {"content": base64.b64encode(data).decode("ascii"), "encoding": "base64"})
        if blob["sha"] != sha:
            raise SystemExit(f"blob sha mismatch for {path}")
        entries.append({"path": path, "mode": mode, "type": "blob", "sha": blob["sha"]})
    for path in deleted:
        entries.append({"path": path, "mode": "100644", "type": "blob", "sha": None})

    if not entries:
        print("nothing to push - the branch is already up to date")
        return 0

    tree = api("POST", f"/repos/{REPO}/git/trees",
               {"base_tree": base_tree, "tree": entries})
    print(f"new tree : {tree['sha']}")

    message = os.environ.get(
        "FZMM_MSG",
        "Port to Minecraft 26.3\n\n"
        "- GLFW -> SDL3 input constants (InputConstants.KEY_*), Type.KEYSYM -> Type.KEYBOARD\n"
        "- Util.getPlatform().openFile -> Blaze3D.openPath\n"
        "- ConfirmLinkScreen.confirmLinkNow now takes a java.net.URI\n"
        "- ItemContainerContents.allItemsCopyStream -> nonEmptyItemCopyStream\n"
        "- authlib yggdrasil package moved to authlib.services\n"
        "- GameRenderer.renderItemInHand injection point updated for renderpearl\n"
        "- fabric.mod.json minecraft constraint ~26.2 -> ~26.3\n"
        "- VersionArgumentType: added 26.2 and 26.3\n",
    )
    new_commit = api("POST", f"/repos/{REPO}/git/commits", {
        "message": message,
        "tree": tree["sha"],
        "parents": [BASE],
    })
    print(f"commit   : {new_commit['sha']}")

    try:
        existing = api("GET", f"/repos/{REPO}/git/refs/heads/{BRANCH}")
        api("PATCH", f"/repos/{REPO}/git/refs/heads/{BRANCH}",
            {"sha": new_commit["sha"], "force": False})
        print(f"updated branch {BRANCH}")
    except urllib.error.HTTPError:
        api("POST", f"/repos/{REPO}/git/refs",
            {"ref": f"refs/heads/{BRANCH}", "sha": new_commit["sha"]})
        print(f"created branch {BRANCH}")

    print(f"\nhttps://github.com/{REPO}/tree/{BRANCH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
