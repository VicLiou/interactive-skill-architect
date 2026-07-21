#!/usr/bin/env python3
"""_shared.py — scripts/ 的共用常數與工具（單一真相，避免多處漂移）。

唯讀、無副作用：本模組只讀檔與計算，不寫入/刪除任何檔案（呼應 style-guide.md §13.2）。
內容：
  - 二進位判定（內容嗅探為主、副檔名為輔，§13.4）、SHA256 指紋（SEC-4）、資源上限常數（§13.3）
    —— validate-skill.py 與 scan-security.py 共用。
  - eval 機械項解析與評分（parse_mechanical／score_mechanical）
    —— score-eval.py 與 verify-cases.py 共用；確定性，無網路/LLM/時間相依（§13.4）。
"""
import os, re, hashlib

# 單檔最多讀 10MB，避免超大檔造成 DoS（§13.3 資源上限）
MAX_BYTES = 10 * 1024 * 1024
# 單次掃描最多處理檔數，避免超深/超大樹拖垮執行（§13.3 資源上限）
MAX_FILES = 20000

# 已知二進位副檔名：內容嗅探的「輔助」白名單（主判定為 sniff_binary 的內容嗅探）。
BINARY_EXTS = {".pyc", ".pyo", ".so", ".o", ".a", ".dll", ".dylib", ".exe", ".bin", ".class",
               ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp", ".tiff",
               ".pdf", ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar",
               ".woff", ".woff2", ".ttf", ".otf", ".eot",
               ".mp3", ".mp4", ".wav", ".avi", ".mov", ".mkv", ".flac",
               ".db", ".sqlite", ".pickle", ".pkl", ".npy", ".npz", ".parquet"}

_TEXT_BYTES = set(range(0x20, 0x7f)) | set(b"\n\r\t\f\b\x1b")


def sniff_binary(path, sample=8192):
    """內容嗅探判定二進位（§13.4：以內容為主、副檔名為輔，防改名繞過）。

    回傳 True 表示應視為二進位（機器驗證須排除、資安掃描須改列指紋）。
    關鍵：UTF-16 文字（PowerShell 常見）雖含 NUL，必須判為「文字」而非二進位，
    以免 UTF-16 腳本被當二進位而整個逃過掃描——用 NUL 的奇偶位分布來區分。
    無法讀取時退回副檔名判定。
    """
    ext = os.path.splitext(path)[1].lower()
    try:
        with open(path, "rb") as f:
            chunk = f.read(sample)
    except Exception:
        return ext in BINARY_EXTS
    if not chunk:
        return False
    if chunk[:2] in (b"\xff\xfe", b"\xfe\xff"):   # UTF-16 BOM → 文字
        return False
    if b"\x00" not in chunk:                        # 無 NUL：多半是文字（含 latin-1）
        return False
    # 含 NUL：區分 UTF-16 文字（NUL 集中於單一奇偶位）與真二進位（NUL 散布）
    evens = chunk[0::2]
    odds = chunk[1::2]
    null_even = evens.count(0)
    null_odd = odds.count(0)
    total_null = null_even + null_odd
    if total_null and max(null_even, null_odd) / total_null > 0.9:
        return False                                # UTF-16 文字
    return True                                     # 視為二進位


def is_binary(path):
    """綜合判定：內容嗅探為主，已知副檔名為輔。"""
    return sniff_binary(path) or os.path.splitext(path)[1].lower() in BINARY_EXTS


def sha256_of(path):
    """計算檔案 SHA256（SEC-4 身分驗證/掉包偵測）；無法讀取回傳 None。"""
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for blk in iter(lambda: f.read(65536), b""):
                h.update(blk)
    except Exception:
        return None
    return h.hexdigest()


# ---------- eval 機械項（score-eval.py 與 verify-cases.py 共用；確定性、無副作用）----------

def parse_mechanical(case_text):
    """從 case frontmatter 抽出 mechanical 的三個清單。極簡 YAML 子集解析，不依賴 pyyaml。

    回傳 {"must_appear": [...], "must_not_appear": [...], "ordering": [(a,b),...]}；
    無 frontmatter 或無 mechanical 區塊回傳 None。
    """
    m = re.match(r"^---\s*\n(.*?)\n---", case_text, re.S)
    if not m:
        return None
    fm = m.group(1)
    mb = re.search(r"^mechanical:\s*\n(.*?)(?=^\S|\Z)", fm + "\n", re.S | re.M)
    if not mb:
        return None
    block = mb.group(1)
    out = {"must_appear": [], "must_not_appear": [], "ordering": []}
    cur = None
    for line in block.splitlines():
        key = re.match(r"\s{2}(must_appear|must_not_appear|ordering):\s*$", line)
        if key:
            cur = key.group(1)
            continue
        item = re.match(r"\s{4}-\s*(.+?)\s*$", line)
        if item and cur:
            val = item.group(1).strip()
            if val.startswith("#"):
                continue                       # 註解行，跳過
            if cur == "ordering":
                pair = re.findall(r'"([^"]*)"|\'([^\']*)\'|([^\[\],]+)', val)
                flat = [a or b or c for a, b, c in pair if (a or b or c).strip()]
                if len(flat) >= 2:
                    out["ordering"].append((flat[0].strip(), flat[1].strip()))
            else:
                out[cur].append(val.strip().strip('"').strip("'"))
    return out


def score_mechanical(mech, transcript):
    """對逐字稿套用 mechanical 斷言，回傳 [(ok, label, detail), ...]（確定性）。"""
    results = []
    for pat in mech["must_appear"]:
        ok = re.search(pat, transcript) is not None
        results.append((ok, "must_appear", pat + ("" if ok else "  ← 未出現")))
    for pat in mech["must_not_appear"]:
        hit = re.search(pat, transcript)
        results.append((hit is None, "must_not_appear",
                        pat + ("" if hit is None else "  ← 不該出現卻出現: " + hit.group(0)[:60])))
    for a, b in mech["ordering"]:
        ia, ib = transcript.find(a), transcript.find(b)
        ok = ia != -1 and ib != -1 and ia < ib
        results.append((ok, "ordering", a + " → " + b + ("" if ok else "  ← 順序錯誤或缺項")))
    return results


def extract_transcript(case_text, tag):
    """從 case .md 抽出 ```<tag> ... ``` fenced 區塊內容（compliant／violation）；無則回傳 None。"""
    m = re.search(r"```" + re.escape(tag) + r"\s*\n(.*?)```", case_text, re.S)
    return m.group(1) if m else None
