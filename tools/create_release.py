#!/usr/bin/env python3
"""Create a GitHub release (prerelease) and upload the mod jar as an asset.

The git HTTPS transport is unreachable on this network, so the release is
created through the REST API instead of `gh release create`.
"""
import json
import mimetypes
import os
import subprocess
import sys
import urllib.error
import urllib.request

REPO = os.environ.get("FZMM_REPO", "HeCUana/FZMM-Mod")
TAG = os.environ.get("FZMM_TAG", "0.2.21-beta.1")
TARGET = os.environ.get("FZMM_TARGET", "mc26.3")
JAR = os.environ.get("FZMM_JAR", "")
API = "https://api.github.com"
UPLOADS = "https://uploads.github.com"
PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BODY = """## FZMM 0.2.21-beta.1 for Minecraft 26.3

Minecraft 26.3 移植版（beta）。本分支基于上游 `26.2/dev`，上游 `dev` 未改动。

### Highlights
- 移植到 Minecraft **26.3**（SDL3 输入层 + renderpearl 渲染层）
- 依赖 **owo-lib `0.13.1+26.3`**（官方 maven 尚未发布 26.3 版，见下）

### 迁移要点

| 26.2 | 26.3 |
|---|---|
| `GLFW.GLFW_KEY_*` | `InputConstants.KEY_*`（键码空间换成 SDL 风格） |
| `InputConstants.Type.KEYSYM` | `InputConstants.Type.KEYBOARD` |
| `Util.getPlatform().openFile(File)` | `Blaze3D.openPath(Path)` |
| `ConfirmLinkScreen.confirmLinkNow(..., String, ...)` | `..., java.net.URI, ...` |
| `ItemContainerContents.allItemsCopyStream()` | `nonEmptyItemCopyStream()` |
| `authlib.yggdrasil.ProfileResult` | `authlib.services.ProfileResult` |
| `GameRenderer.renderItemInHand(..., float, Matrix4fc)` | `(..., PlayerRenderState, GpuTextureView)` |

### 安装
- Minecraft **26.3**
- [Fabric API](https://modrinth.com/mod/fabric-api) `0.165.2+26.3` 或更高
- [owo-lib](https://modrinth.com/mod/owo-lib) **`0.13.1+26.3`**（官方 maven 暂无此版本，需要本地构建版）

> 本分支不含上游 `dev` 的「Add context menus and related features」提交（右键菜单），
> 该提交晚于 `26.2/dev`。

完整移植说明：https://github.com/""" + REPO + """/blob/""" + TARGET + """/UPGRADE_26_3.md
"""


def get_token():
    out = subprocess.run(["cmd", "/c", "git credential fill < cred-in.txt"],
                         cwd=PROJECT, capture_output=True, text=True, timeout=60)
    for line in out.stdout.splitlines():
        if line.startswith("password="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("no credential")


TOKEN = get_token()
HEADERS = {
    "Authorization": "Bearer " + TOKEN,
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "fzmm-port-tool",
}


def api(method, path, payload=None):
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(API + path, data=body, method=method)
    for k, v in HEADERS.items():
        req.add_header(k, v)
    if body is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = resp.read()
    except urllib.error.HTTPError as e:
        raise SystemExit(f"{method} {path} -> HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:900]}")
    return json.loads(data.decode("utf-8")) if data else None


def upload_asset(release_id, path):
    name = os.path.basename(path)
    size = os.path.getsize(path)
    ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
    url = f"{UPLOADS}/repos/{REPO}/releases/{release_id}/assets?name={name}"
    req = urllib.request.Request(url, method="POST")
    for k, v in HEADERS.items():
        req.add_header(k, v)
    req.add_header("Content-Type", ctype)
    req.add_header("Content-Length", str(size))
    with open(path, "rb") as fh:
        data = fh.read()
    try:
        with urllib.request.urlopen(req, data=data, timeout=600) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise SystemExit(f"upload {name} -> HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:600]}")


def main():
    print(f"repo  : {REPO}")
    print(f"tag   : {TAG}  ->  {TARGET}")

    existing = api("GET", f"/repos/{REPO}/releases/tags/{TAG}") if False else None

    release = api("POST", f"/repos/{REPO}/releases", {
        "tag_name": TAG,
        "target_commitish": TARGET,
        "name": f"FZMM {TAG} for MC 26.3",
        "body": BODY,
        "draft": False,
        "prerelease": True,
        "make_latest": "false",
    })
    print(f"release id : {release['id']}")
    print(f"html       : {release['html_url']}")

    if JAR:
        asset = upload_asset(release["id"], JAR)
        print(f"asset      : {asset['name']}  {asset['size']} bytes  {asset['browser_download_url']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
