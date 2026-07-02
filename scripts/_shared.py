#!/usr/bin/env python3
"""_shared.py — validate-skill.py 與 scan-security.py 的共用常數與工具（單一真相，避免兩處漂移）。

唯讀、無副作用：本模組只讀檔與計算，不寫入/刪除任何檔案（呼應 style-guide.md §13.2）。
內容：二進位判定（內容嗅探為主、副檔名為輔，§13.4）、SHA256 指紋（SEC-4）、資源上限常數（§13.3）。
"""
import os, hashlib

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
