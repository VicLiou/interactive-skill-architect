#!/usr/bin/env python3
"""
verify-cases.py — eval 案例的「元驗證」：確認每個案例的機械斷言真的測到它宣稱的紀律
                  （唯讀，不修改任何檔案）。

用法:
    python3 verify-cases.py <evals_dir>      # 省略則檢查 ./evals

退出碼: 0 = 全部案例合格；1 = 有不合格案例；2 = 執行錯誤（如目錄不存在）。

要解決的問題:
    一個案例可能機械項全綠、卻根本沒測到它 frontmatter 宣稱的紀律（假綠燈）。
    實作 eval 時就發生過：21 條斷言有 2 條在「負向正確句」上誤報（見 evals/README）。
    本工具給「考題」本身加單元測試，堵住這個元層級盲點。

合格判準（每個 case-*.md 都必須通過）:
    1. frontmatter 有可解析的 mechanical 區塊。
    2. 內嵌 ```compliant 逐字稿 → 套用機械斷言必須 **全數 PASS**（正確行為要放行）。
    3. 內嵌 ```violation 逐字稿 → 套用機械斷言必須 **至少一項 FAIL**（破戒行為要抓到）。
    任一不符 → 該案例的斷言無效（假綠燈或抓不到破戒），判 FAIL。

確定性（§13.4）: 無網路、無 LLM、無時間相依；解析與評分邏輯與 score-eval.py 共用 _shared（單一真相）。
由自我測試模式在維護案例時呼叫；也可獨立跑作為案例品質閘門。
"""
import sys, os, glob
sys.dont_write_bytecode = True   # 唯讀承諾（§13.2）
from _shared import parse_mechanical, score_mechanical, extract_transcript   # 單一真相


def verify_one(case_fp):
    """回傳 (ok, [problem, ...])。ok=True 表示案例的斷言有效。"""
    text = open(case_fp, encoding="utf-8", errors="replace").read()
    probs = []
    mech = parse_mechanical(text)
    if mech is None:
        return False, ["frontmatter 缺 mechanical 區塊"]
    n_assert = len(mech["must_appear"]) + len(mech["must_not_appear"]) + len(mech["ordering"])
    if n_assert == 0:
        probs.append("mechanical 無任何斷言（must_appear/must_not_appear/ordering 全空）")

    compliant = extract_transcript(text, "compliant")
    violation = extract_transcript(text, "violation")
    if compliant is None:
        probs.append("缺 ```compliant 逐字稿區塊")
    if violation is None:
        probs.append("缺 ```violation 逐字稿區塊")

    # compliant 必須全數 PASS（正確行為要被放行）
    if compliant is not None:
        rc = score_mechanical(mech, compliant)
        fails = [d for ok, lb, d in rc if not ok]
        if fails:
            probs.append("compliant 逐字稿被誤判 FAIL（正確句不該被抓）: " + "; ".join(fails))

    # violation 必須至少一項 FAIL（破戒行為要被抓到）
    if violation is not None:
        rv = score_mechanical(mech, violation)
        if all(ok for ok, lb, d in rv):
            probs.append("violation 逐字稿全 PASS（破戒卻抓不到——斷言可能沒測到宣稱的紀律）")

    return (len(probs) == 0), probs


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "evals"
    if not os.path.isdir(target):
        print("ERROR: 目錄不存在: " + target)
        return 2
    cases = sorted(glob.glob(os.path.join(target, "case-*.md")))
    if not cases:
        print("ERROR: " + target + " 下找不到 case-*.md")
        return 2

    print("== verify-cases 案例元驗證 ==")
    nbad = 0
    for fp in cases:
        ok, probs = verify_one(fp)
        name = os.path.basename(fp)
        if ok:
            print("[OK]   " + name)
        else:
            nbad += 1
            print("[BAD]  " + name)
            for p in probs:
                print("         - " + p)
    print("-- " + str(len(cases)) + " 案例: " + str(nbad) + " 不合格 --")
    return 1 if nbad else 0


if __name__ == "__main__":
    sys.exit(main())
