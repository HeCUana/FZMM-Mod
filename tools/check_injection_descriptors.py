#!/usr/bin/env python3
"""
Verify that every descriptor-form mixin injection target still exists verbatim
in the Minecraft 26.3 deobfuscated jar.

The name-only audit in audit_mixins_263.py cannot catch a method whose
*signature* changed while keeping its name, which is exactly the failure mode
for mixins that declare `method = "name(Ldescriptor;)V"`.
"""
import os
import re
import subprocess
import sys
import zipfile

MC_JAR = os.path.expandvars(
    r"%USERPROFILE%\.gradle\caches\fabric-loom\minecraftMaven\net\minecraft"
    r"\minecraft-merged-deobf\26.3\minecraft-merged-deobf-26.3.jar"
)
JAVAP = os.environ.get("JAVAP", r"C:\Program Files\Zulu\zulu-26\bin\javap.exe")
if not os.path.exists(JAVAP):
    JAVAP = "javap"

# class -> list of "name(descriptor)" targets taken from the mixin sources
TARGETS = {
    "net.minecraft.client.renderer.entity.ItemFrameRenderer": [
        "extractRenderState(Lnet/minecraft/world/entity/decoration/ItemFrame;"
        "Lnet/minecraft/client/renderer/entity/state/ItemFrameRenderState;F)V",
    ],
    "net.minecraft.world.item.CreativeModeTab$ItemDisplayParameters": [
        "needsUpdate(Lnet/minecraft/world/flag/FeatureFlagSet;Z"
        "Lnet/minecraft/core/HolderLookup$Provider;)Z",
    ],
    "net.minecraft.client.gui.components.EditBox": [
        "insertText(Ljava/lang/String;)V",
        "charTyped(Lnet/minecraft/client/input/CharacterEvent;)Z",
    ],
    "net.minecraft.client.gui.screens.ChatScreen": [
        "onEdited(Ljava/lang/String;)V",
        "moveInHistory(I)V",
        "normalizeChatMessage(Ljava/lang/String;)Ljava/lang/String;",
    ],
    "net.minecraft.client.gui.components.ChatComponent": [
        "extractRenderState(Lnet/minecraft/client/gui/GuiGraphicsExtractor;"
        "Lnet/minecraft/client/gui/Font;IIILnet/minecraft/client/gui/components/"
        "ChatComponent$DisplayMode;Z)V",
    ],
    "net.minecraft.client.renderer.GameRenderer": [
        "renderItemInHand(Lnet/minecraft/client/renderer/state/level/CameraRenderState;"
        "Lnet/minecraft/client/renderer/state/level/PlayerRenderState;"
        "Lcom/mojang/renderpearl/api/textures/GpuTextureView;)V",
    ],
}


def javap_descriptors(fqcn):
    """Return the set of 'name(descriptor)' strings declared by fqcn."""
    out = subprocess.run(
        [JAVAP, "-p", "-s", "-cp", MC_JAR, fqcn],
        capture_output=True, text=True, timeout=60,
    )
    if out.returncode != 0:
        return None
    result = set()
    lines = out.stdout.splitlines()
    for i, line in enumerate(lines):
        line = line.strip()
        if not line.endswith(");"):
            continue
        m = re.match(r"^(?:[\w$.<>\[\], ]+\s+)?([\w$]+)\((.*)\);$", line)
        if not m:
            continue
        name, params = m.group(1), m.group(2)
        # the descriptor line follows the declaration
        for j in range(i + 1, min(i + 4, len(lines))):
            d = lines[j].strip()
            if d.startswith("descriptor:"):
                result.add(f"{name}{d.split('descriptor:', 1)[1].strip()}")
                break
    return result


def main():
    problems = []
    for cls, wanted in TARGETS.items():
        descs = javap_descriptors(cls)
        if descs is None:
            problems.append((cls, "class not found / javap failed"))
            continue
        for w in wanted:
            if w in descs:
                print(f"  OK    {cls} :: {w}")
            else:
                problems.append((cls, w))

    print()
    if problems:
        print(f"MISMATCHES ({len(problems)}):")
        for cls, what in problems:
            print(f"  !! {cls} :: {what}")
            got = javap_descriptors(cls)
            if got:
                near = [g for g in sorted(got) if g.split("(")[0] == what.split("(")[0]]
                for n in near:
                    print(f"       actual: {n}")
        return 1

    print("all descriptor-form injection targets match MC 26.3 verbatim")
    return 0


if __name__ == "__main__":
    sys.exit(main())
