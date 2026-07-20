#!/usr/bin/env python3
"""
score-eval.py — 對一份 eval 案例的「機械項」做確定性評分（唯讀，不修改任何檔案）。

用法:
    python3 score-eval.py <case_file> <transcript_file>

輸入:
    <case_file>       evals/case-*.md，frontmatter 需含 mechanical 區塊。
    <transcript_file> 被測流程重放後的對話逐字稿（純文字；由 eval-mode Phase E2 產生）。

退出碼: 0 = 全部機械項 PASS；1 = 有機械項 FAIL；2 = 執行錯誤（路徑不存在／frontmatter 缺 mechanical）。

定位: 這是自我測試模式 Phase E2 的「機械項評分器」，只判定可確定性檢查的斷言
      （某字串必須出現 / 必須不出現 / 出現順序）。語意項（是否量身打造、是否理解意圖）
      不在此腳本，交由 judge——呼應 style-guide.md §13.4 機器 vs 語意分界。

確定性保證（§13.4）: 無網路、無 LLM、無時間相依；同輸入必得同結果、可重現。

機械項 frontmatter 格式（YAML 子集，本腳本自解析，不依賴 pyyaml）:
    mechanical:
      must_appear:          # 這些 regex 必須在逐字稿中出現（缺一即 FAIL）
        - "【建立模式・Phase 1 開始】"
      must_not_appear:      # 這些 regex 必須不出現（出現即 FAIL）
        - "Q[0-9].*Q[0-9]"  # 例：同輪出現兩個 Q 編號＝違規合併提問
      ordering:             # 選用：這些片語必須依序出現（前者先於後者）
        - ["Phase 1", "Phase 4"]
"""
import sys, os, re
sys.dont_write_bytecode = True   # 唯讀承諾（§13.2）


def parse_mechanical(case_text):
    """從 case frontmatter 抽出 mechanical 的三個清單。極簡 YAML 子集解析，不依賴外部套件。"""
    m = re.match(r"^---\s*\n(.*?)\n---", case_text, re.S)
    if not m:
        return None
    fm = m.group(1)
    # 取 mechanical: 到下一個頂層鍵（或結尾）之間的區塊
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
            if cur == "ordering":
                pair = re.findall(r'"([^"]*)"|\'([^\']*)\'|([^\[\],]+)', val)
                flat = [a or b or c for a, b, c in pair if (a or b or c).strip()]
                if len(flat) >= 2:
                    out["ordering"].append((flat[0].strip(), flat[1].strip()))
            else:
                out[cur].append(val.strip().strip('"').strip("'"))
    return out


def main():
    if len(sys.argv) < 3:
        print("用法: python3 score-eval.py <case_file> <transcript_file>")
        return 2
    case_fp, tr_fp = sys.argv[1], sys.argv[2]
    for fp in (case_fp, tr_fp):
        if not os.path.isfile(fp):
            print("ERROR: 檔案不存在: " + fp)
            return 2
    mech = parse_mechanical(open(case_fp, encoding="utf-8", errors="replace").read())
    if mech is None:
        print("ERROR: case frontmatter 缺 mechanical 區塊，無法機械評分")
        return 2
    tr = open(tr_fp, encoding="utf-8", errors="replace").read()

    results = []  # (ok, label, detail)
    for pat in mech["must_appear"]:
        ok = re.search(pat, tr) is not None
        results.append((ok, "must_appear", pat + ("" if ok else "  ← 未出現")))
    for pat in mech["must_not_appear"]:
        hit = re.search(pat, tr)
        results.append((hit is None, "must_not_appear",
                        pat + ("" if hit is None else "  ← 不該出現卻出現: " + hit.group(0)[:60])))
    for a, b in mech["ordering"]:
        ia, ib = tr.find(a), tr.find(b)
        ok = ia != -1 and ib != -1 and ia < ib
        results.append((ok, "ordering", a + " → " + b + ("" if ok else "  ← 順序錯誤或缺項")))

    print("== score-eval 機械項評分 ==")
    print("case: " + os.path.basename(case_fp))
    for ok, label, detail in results:
        print("[" + ("PASS" if ok else "FAIL") + "] " + label + ": " + detail)
    nf = sum(1 for r in results if not r[0])
    print("-- " + str(len(results)) + " 項機械斷言: " + str(nf) + " FAIL（語意項另由 judge 評分）--")
    return 1 if nf else 0


if __name__ == "__main__":
    sys.exit(main())
