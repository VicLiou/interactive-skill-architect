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

機械項 frontmatter 格式（YAML 子集，解析器見 _shared.parse_mechanical，不依賴 pyyaml）:
    mechanical:
      must_appear:          # 這些 regex 必須在逐字稿中出現（缺一即 FAIL）
        - "【建立模式・Phase 1 開始】"
      must_not_appear:      # 這些 regex 必須不出現（出現即 FAIL）
        - "Q[0-9].*Q[0-9]"  # 例：同輪出現兩個 Q 編號＝違規合併提問
      ordering:             # 選用：這些片語必須依序出現（前者先於後者）
        - ["Phase 1", "Phase 4"]

解析與評分邏輯集中在 _shared.py（與 verify-cases.py 單一真相共用）。
"""
import sys, os
sys.dont_write_bytecode = True   # 唯讀承諾（§13.2）
from _shared import parse_mechanical, score_mechanical   # 單一真相


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
    results = score_mechanical(mech, tr)

    print("== score-eval 機械項評分 ==")
    print("case: " + os.path.basename(case_fp))
    for ok, label, detail in results:
        print("[" + ("PASS" if ok else "FAIL") + "] " + label + ": " + detail)
    nf = sum(1 for r in results if not r[0])
    print("-- " + str(len(results)) + " 項機械斷言: " + str(nf) + " FAIL（語意項另由 judge 評分）--")
    return 1 if nf else 0


if __name__ == "__main__":
    sys.exit(main())
