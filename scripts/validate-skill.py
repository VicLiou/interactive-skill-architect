#!/usr/bin/env python3
"""
validate-skill.py — 對一個 Skill 資料夾做「確定性」的機械檢查（唯讀，不修改任何檔案）。

用法:
    python3 validate-skill.py <skill_dir>     # 省略則檢查當前目錄

退出碼: 0 = 無 FAIL；1 = 有 FAIL；2 = 執行錯誤（如路徑不存在）。

範圍: 只做機械可判定項（編碼/NUL/截斷、kebab-case、name＝資料夾、YAML、
      description、Gotchas 結構、孤兒檔）。語意項（量身打造、Gotchas 覆蓋率、
      步驟邏輯一致性）仍須由 Agent 判斷——本工具不取代語意審查。

由 interactive-skill-architect 的建立模式（Phase 4／寫入後）與優化模式
（Phase O1 預檢／Phase O3 放行前）呼叫；環境無法執行時退回人工檢查。
"""
import sys, os, re, glob

def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    if not os.path.isdir(target):
        print(f"ERROR: 路徑不存在或非資料夾: {target}")
        return 2
    results = []
    add = lambda lv, nm, dt: results.append((lv, nm, dt))

    files = [p for p in glob.glob(os.path.join(target, "**", "*"), recursive=True)
             if os.path.isfile(p)]

    # 已知二進位副檔名：這些跳過文字驗證；其餘一律驗 UTF-8/NUL（反向判定，避免白名單漏網）。
    BINARY_EXTS = {".pyc",".pyo",".so",".o",".a",".dll",".dylib",".exe",".bin",".class",
                   ".png",".jpg",".jpeg",".gif",".bmp",".ico",".webp",".tiff",
                   ".pdf",".zip",".tar",".gz",".bz2",".xz",".7z",".rar",
                   ".woff",".woff2",".ttf",".otf",".eot",
                   ".mp3",".mp4",".wav",".avi",".mov",".mkv",".flac",
                   ".db",".sqlite",".pickle",".pkl",".npy",".npz",".parquet"}

    # 1. 編碼/完整性（預設驗所有檔的 NUL + UTF-8；僅已知二進位副檔名跳過，避免漏驗）
    probs, bins = [], []
    for p in files:
        rel = os.path.relpath(p, target).replace(os.sep, "/")
        ext = os.path.splitext(p)[1].lower()
        try:
            b = open(p, "rb").read()
        except Exception as e:
            probs.append(f"{rel}: 無法讀取 ({e})"); continue
        if ext in BINARY_EXTS:
            bins.append(rel); continue          # 已知二進位資產：跳過文字驗證
        if b"\x00" in b:
            probs.append(f"{rel}: 含 NUL 位元組（若為未列入的二進位請補列 BINARY_EXTS，否則疑似損壞）")
        try:
            b.decode("utf-8")
        except UnicodeDecodeError as e:
            probs.append(f"{rel}: UTF-8 解析失敗 @ byte {e.start}（可能尾字被截斷）")
    add("FAIL" if probs else "PASS", "編碼/完整性",
        "; ".join(probs) or "所有文字檔合法 UTF-8、無 NUL")
    # 二進位檔提示：scripts/ 下的二進位需確認是否應納入 Skill（依 style-guide §9）
    if bins:
        in_scripts = [r for r in bins if r.startswith("scripts/")]
        add("WARN" if in_scripts else "PASS", "二進位檔偵測",
            (f"scripts/ 含二進位（確認是否應納入）: {', '.join(in_scripts)}; " if in_scripts else "")
            + f"已略過文字驗證: {', '.join(bins)}")

    # 2. SKILL.md 存在
    sp = os.path.join(target, "SKILL.md")
    if not os.path.isfile(sp):
        add("FAIL", "SKILL.md 存在", "找不到 SKILL.md")
        return report(results)
    skill = open(sp, encoding="utf-8", errors="replace").read()

    # 3. kebab-case 資料夾 + name 一致 + description
    folder = os.path.basename(os.path.abspath(target))
    add("PASS" if re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", folder) else "FAIL",
        "kebab-case 資料夾", folder if re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", folder) else f"不符 kebab-case: {folder}")
    m = re.match(r"^---\s*\n(.*?)\n---", skill, re.S)
    if not m:
        add("FAIL", "YAML frontmatter", "找不到 frontmatter")
    else:
        fm = m.group(1)
        nm = re.search(r"^name:\s*(.+?)\s*$", fm, re.M)
        if not nm: add("FAIL", "name 欄位", "frontmatter 無 name")
        elif nm.group(1).strip() != folder: add("WARN", "name＝資料夾", f"name={nm.group(1).strip()} ≠ 資料夾={folder}")
        else: add("PASS", "name＝資料夾", folder)
        add("PASS" if "description:" in fm else "FAIL", "description", "有 description" if "description:" in fm else "frontmatter 無 description")

    # 4. Gotchas 結構
    g = []
    if "## Gotchas" not in skill: g.append("無 ## Gotchas")
    if "[!WARNING]" not in skill: g.append("無 [!WARNING] 區塊")
    if "\U0001F504" not in skill: g.append("無 🔄 迭代註腳")
    add("FAIL" if "無 ## Gotchas" in g else ("WARN" if g else "PASS"),
        "Gotchas 結構", "; ".join(g) or "WARNING 區塊與迭代註腳齊全")

    # 5. 孤兒檔偵測（references/assets/scripts 下的檔是否被任一 .md 提及）
    md = "\n".join(open(p, encoding="utf-8", errors="replace").read()
                   for p in files if p.endswith(".md"))
    orphans = []
    for p in files:
        rel = os.path.relpath(p, target).replace(os.sep, "/")
        if rel == "SKILL.md": continue
        if os.path.basename(p) not in md and rel not in md:
            orphans.append(rel)
    add("WARN" if orphans else "PASS", "孤兒檔偵測",
        ("未被任何 .md 引用: " + ", ".join(orphans)) if orphans else "無孤兒檔")

    # 6. 體積預算（數字依 style-guide §12，為單一真相；改動需同步 §12）
    #    SKILL.md 為每次必載入口，最嚴；references 按需載入，放寬；assets/scripts 不計入。
    def est_tokens(s):
        cjk = sum(1 for ch in s if '一' <= ch <= '鿿' or '぀' <= ch <= 'ヿ')
        return int(cjk * 1.7 + (len(s) - cjk) / 4)   # 粗估：CJK≈1.7 token/字，其餘≈4 char/token
    sl, st = skill.count("\n") + 1, est_tokens(skill)   # 行數含空白行與 frontmatter（保守）
    size_probs = []
    if sl > 500:  size_probs.append(f"SKILL.md {sl} 行 > 500（FAIL，§12 硬上限）")
    if st > 5000: size_probs.append(f"SKILL.md 估算 ~{st} token > 5000（WARN，§12 軟上限）")
    for p in files:
        rel = os.path.relpath(p, target).replace(os.sep, "/")
        if rel.startswith("references/") and rel.endswith(".md"):
            n = open(p, encoding="utf-8", errors="replace").read().count("\n") + 1
            if n > 800: size_probs.append(f"{rel} {n} 行 > 800（WARN）")
    add("FAIL" if sl > 500 else ("WARN" if size_probs else "PASS"), "體積預算",
        "; ".join(size_probs) or f"SKILL.md {sl} 行 / ~{st} token，references 均在上限內")

    return report(results)

def report(results):
    mk = {"PASS": "PASS", "WARN": "WARN", "FAIL": "FAIL"}
    print("== validate-skill 機械檢查報告 ==")
    for lv, nm, dt in results:
        print(f"[{mk[lv]}] {nm}: {dt}")
    nf = sum(1 for r in results if r[0] == "FAIL")
    nw = sum(1 for r in results if r[0] == "WARN")
    print(f"-- {len(results)} 項: {nf} FAIL / {nw} WARN（語意項仍須 Agent 判斷）--")
    return 1 if nf else 0

if __name__ == "__main__":
    sys.exit(main())
