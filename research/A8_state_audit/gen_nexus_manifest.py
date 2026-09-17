"""gen_nexus_manifest.py — 生成 NEXUS_SOURCE_MANIFEST.json（方案 §十五 B）。

TYPE:INFRA（research/ 隔离层）

扫描 tss/ 与 research/ 全部 .py 的 import 语句，解析出实际引用的 nexus_v1
模块，落盘每个源文件的 relative path + SHA256 + 当前 git commit。交付包
携带该 manifest 后，外部无需母体源码即可校验其手中的 nexus_v1 副本与
VERSION.txt 声明的 commit 一致。

用法：python research/A8_state_audit/gen_nexus_manifest.py
输出：NEXUS_SOURCE_MANIFEST.json（repo 根）
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
_IMPORT_RE = re.compile(
    r"^\s*(?:from\s+(nexus_v1(?:\.\w+)*)\s+import|import\s+(nexus_v1(?:\.\w+)*))",
    re.M)


def scan_imports() -> set[str]:
    mods: set[str] = set()
    for top in ("tss", "research"):
        for root, _dirs, files in os.walk(os.path.join(REPO, top)):
            for fn in files:
                if not fn.endswith(".py"):
                    continue
                with open(os.path.join(root, fn), encoding="utf-8",
                          errors="replace") as f:
                    for m in _IMPORT_RE.finditer(f.read()):
                        mods.add(m.group(1) or m.group(2))
    return mods


def module_files(mods: set[str]) -> list[str]:
    """模块名 → 源文件相对路径（含所属包的 __init__.py 链）。"""
    files: set[str] = set()
    for mod in sorted(mods):
        parts = mod.split(".")
        # 包链 __init__.py
        for i in range(1, len(parts)):
            init = os.path.join(*parts[:i], "__init__.py")
            if os.path.exists(os.path.join(REPO, init)):
                files.add(init)
        leaf_py = os.path.join(*parts) + ".py"
        leaf_init = os.path.join(*parts, "__init__.py")
        if os.path.exists(os.path.join(REPO, leaf_py)):
            files.add(leaf_py)
        elif os.path.exists(os.path.join(REPO, leaf_init)):
            files.add(leaf_init)
        else:
            print(f"  [warn] 未找到模块源文件: {mod}")
    return sorted(f.replace(os.sep, "/") for f in files)


def main() -> int:
    mods = scan_imports()
    files = module_files(mods)
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO,
                            capture_output=True, text=True).stdout.strip()
    entries = []
    for rel in files:
        with open(os.path.join(REPO, rel), "rb") as f:
            sha = hashlib.sha256(f.read()).hexdigest()
        entries.append({"path": rel, "sha256": sha})
    manifest = {"expected_commit": commit,
                "generated_by": "research/A8_state_audit/gen_nexus_manifest.py",
                "imported_nexus_modules": sorted(mods),
                "files": entries}
    out_path = os.path.join(REPO, "NEXUS_SOURCE_MANIFEST.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"nexus_v1 模块 {len(mods)} 个 → 源文件 {len(entries)} 个")
    print(f"expected_commit = {commit}")
    print(f"落盘: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
