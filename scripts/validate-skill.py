#!/usr/bin/env python3
"""
validate-skill.py — 對一個 Skill 資料夾做「確定性」的機械檢查（唯讀，不修改任何檔案）。

用法:
    python3 validate-skill.py <skill_dir>     # 省略則檢查當前目錄

退出碼: 0 = 無 FAIL；1 = 有 FAIL；2 = 執行錯誤（如路徑不存在）。

範圍: 只做機械可判定項（編碼/NUL/截斷、kebab-case、name＝資料夾、YAML、
      description、Gotchas 結構、孤兒檔、懸空引用、體積預算）。語意項（量身打造、
      Gotchas 覆蓋率、步驟邏輯一致性）仍須由 Agent 判斷——本工具不取代語意審查。
      孤兒檔＝檔案存在但沒被任何 .md 引用；懸空引用＝.md 承諾載入但檔案不存在（互為反向）。

由 interactive-skill-architect 的建立模式（Phase 4／寫入後）與優化模式
（Phase O1 預檢／Phase O3 放行前）呼叫；環境無法執行時退回人工檢查。
"""
import sys, os, re
sys.dont_write_bytecode = True   # 唯讀承諾（§13.2）：禁止 import 產生 __pycache__，須在 import _shared 之前設定
from _shared import BINARY_EXTS, is_binary, MAX_BYTES, MAX_FILES   # 單一真相：共用常數與二進位嗅探

def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    if not os.path.isdir(target):
        print(f"ERROR: 路徑不存在或非資料夾: {target}")
        return 2
    results = []
    add = lambda lv, nm, dt: results.append((lv, nm, dt))

    # 檔案走訪（§13.3）：os.walk 預設不跟隨 symlink 目錄（glob 會，故不用）；
    # 沿用先前行為略過隱藏檔（含 .git）；檔數上限 MAX_FILES 防超大樹 DoS。
    files, truncated = [], False
    for root, dirs, fnames in os.walk(target):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for fn in fnames:
            if fn.startswith("."):
                continue
            if len(files) >= MAX_FILES:
                truncated = True
                break
            fp = os.path.join(root, fn)
            if os.path.isfile(fp) or os.path.islink(fp):
                files.append(fp)
        if truncated:
            break
    if truncated:
        add("WARN", "走訪上限", f"檔案數達上限 {MAX_FILES}，檢查已截斷；請分區重驗或人工確認剩餘檔案")

    # 二進位判定改為「內容嗅探為主、副檔名為輔」（style-guide §13.4），
    # 防止把二進位改名成 .md/.txt 繞過文字驗證；BINARY_EXTS 由 _shared 提供（單一真相）。

    # 1. 編碼/完整性（預設驗所有檔的 NUL + UTF-8；被判定為二進位者跳過文字驗證）
    probs, bins, masq = [], [], []
    for p in files:
        rel = os.path.relpath(p, target).replace(os.sep, "/")
        ext = os.path.splitext(p)[1].lower()
        if os.path.islink(p):                    # symlink：不讀內容（§13.3），只記錄
            probs.append(f"{rel}: 為符號連結，已跳過（指向 {os.readlink(p)}；請人工確認未逃逸資料夾）")
            continue
        try:
            if os.path.getsize(p) > MAX_BYTES:   # 資源上限（§13.3）：超大檔不整檔載入，明確告警而非靜默通過
                probs.append(f"{rel}: 超過單檔上限 {MAX_BYTES // (1024*1024)}MB，未驗證（請人工確認）")
                continue
            b = open(p, "rb").read()
        except Exception as e:
            probs.append(f"{rel}: 無法讀取 ({e})"); continue
        if is_binary(p):                         # 內容嗅探或已知副檔名 → 視為二進位，跳過文字驗證
            bins.append(rel)
            if ext not in BINARY_EXTS:           # 內容像二進位卻用文字副檔名 → 疑似偽裝
                masq.append(rel)
            continue
        if b"\x00" in b:
            probs.append(f"{rel}: 含 NUL 位元組（疑似損壞或未被嗅探識別的二進位）")
        try:
            b.decode("utf-8")
        except UnicodeDecodeError as e:
            probs.append(f"{rel}: UTF-8 解析失敗 @ byte {e.start}（可能尾字被截斷）")
    add("FAIL" if probs else "PASS", "編碼/完整性",
        "; ".join(probs) or "所有文字檔合法 UTF-8、無 NUL")
    # 二進位檔提示：scripts/ 下的二進位、或內容像二進位卻偽裝成文字副檔名者需人工確認（依 §9／§13.4）
    if bins:
        in_scripts = [r for r in bins if r.startswith("scripts/")]
        detail = ""
        if in_scripts:
            detail += f"scripts/ 含二進位（確認是否應納入並登錄 SHA256/來源）: {', '.join(in_scripts)}; "
        if masq:
            detail += f"內容疑似二進位卻用文字副檔名（可能偽裝）: {', '.join(masq)}; "
        detail += f"已略過文字驗證: {', '.join(bins)}"
        add("WARN" if (in_scripts or masq) else "PASS", "二進位檔偵測", detail)

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
    #    先剝除 HTML 註解，避免「只在 <!-- ... --> 註解裡被提及」被誤算成有效引用。
    raw_md = "\n".join(open(p, encoding="utf-8", errors="replace").read()
                       for p in files if p.endswith(".md"))
    md = re.sub(r"<!--.*?-->", "", raw_md, flags=re.S)   # 註解不算引用
    orphans = []
    META_FILES = {"SKILL.md", "LICENSE", "LICENSE.txt", "LICENSE.md", "NOTICE"}  # 慣例後設檔不算孤兒
    # 以 glob 樣式（如 `case-*.md`）集體引用的資料夾（fixture/資料集），成員不逐一具名，不算孤兒。
    glob_refd = re.findall(r"([A-Za-z0-9._/-]*\*[A-Za-z0-9._/-]*\.[A-Za-z0-9]+)", md)
    glob_rx = [re.compile("^" + re.escape(g).replace(r"\*", "[^/]*") + "$") for g in glob_refd]
    for p in files:
        rel = os.path.relpath(p, target).replace(os.sep, "/")
        base = os.path.basename(p)
        if rel in META_FILES or base == "README.md": continue  # README 自我說明其所在資料夾，非被載入的 reference
        if os.path.basename(p) in md or rel in md: continue
        if any(rx.match(rel) or rx.match(os.path.basename(p)) for rx in glob_rx): continue  # 被 glob 集體引用
        orphans.append(rel)
    add("WARN" if orphans else "PASS", "孤兒檔偵測",
        ("未被任何 .md 引用（不含註解內提及）: " + ", ".join(orphans)) if orphans else "無孤兒檔")

    # 5b. 懸空引用偵測（dangling reference）：檔案承諾「載入／執行」某檔，但該檔實際不存在。
    #     比孤兒檔更危險——Agent 執行時會載入失敗。
    #     為避免誤報，只在兩個條件同時成立時才判懸空：
    #       (a) 路徑出現在**載入語境**（同行含 載入/引用/依/跑/執行/python3 等動詞），
    #           排除純示意的「如 xxx.md」「例如」列舉；
    #       (b) 來源檔**不是** assets/examples/**（示範用的假 skill）或 *template*（含佔位路徑）。
    #     這兩類檔合法地含有「別的 skill 的」或「佔位的」路徑，不該當成本 skill 的承諾。
    #     另兩個示意來源也須排除：``` 圍籬碼區塊內的**格式示例**、以及緊接在
    #     「如／例如／比如」後的**舉例路徑**——這些是規範文件在示範寫法，不是真實載入承諾。
    present = {os.path.relpath(p, target).replace(os.sep, "/") for p in files}
    LOAD_KW = re.compile(r"載入|引用|讀取|依\s*`|跑\s*`|執行|python3|見\s*`")
    path_rx = re.compile(r"(?:references|assets|scripts)/[A-Za-z0-9._/-]+\.(?:md|py|sh|txt|json|ya?ml)")
    ILLUS = re.compile(r"(如|例如|比如|像|類似)\s*`?\s*$")   # 路徑前是舉例語 → 示意，非承諾
    dangling = set()
    for p in files:
        rel = os.path.relpath(p, target).replace(os.sep, "/")
        if not rel.endswith(".md"): continue
        if rel.startswith("assets/examples/") or "template" in os.path.basename(rel):
            continue
        body = open(p, encoding="utf-8", errors="replace").read()
        body = re.sub(r"<!--.*?-->", "", body, flags=re.S)   # 註解
        body = re.sub(r"```.*?```", "", body, flags=re.S)     # 圍籬碼內的格式示例
        for line in body.splitlines():
            if not LOAD_KW.search(line): continue
            for mm in path_rx.finditer(line):
                m = mm.group(0)
                if re.search(r"[{}<>*]", m): continue         # 佔位路徑
                if ILLUS.search(line[:mm.start()]): continue  # 「如 xxx」舉例
                if m not in present:
                    dangling.add(m)
    dangling = sorted(dangling)
    add("FAIL" if dangling else "PASS", "懸空引用偵測",
        ("承諾載入但不存在的檔案: " + ", ".join(dangling)) if dangling else "無懸空引用")

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
