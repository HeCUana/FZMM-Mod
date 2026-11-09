#!/usr/bin/env python3
"""Find which classes in the MC 26.3 jar declare a given method name."""
import os
import re
import sys
import zipfile

MC_JAR = os.path.expandvars(
    r"%USERPROFILE%\.gradle\caches\fabric-loom\minecraftMaven\net\minecraft"
    r"\minecraft-merged-deobf\26.3\minecraft-merged-deobf-26.3.jar"
)

needles = sys.argv[1:] or ["openFile"]

with zipfile.ZipFile(MC_JAR) as z:
    for entry in z.namelist():
        if not entry.endswith(".class"):
            continue
        data = z.read(entry)
        for needle in needles:
            # method names live in the constant pool as plain UTF8 entries
            if re.search((r"\b" + re.escape(needle) + r"\b").encode("latin-1"), data):
                print(f"{entry[:-6].replace('/', '.')}  <- contains '{needle}'")
