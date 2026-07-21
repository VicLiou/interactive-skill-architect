# Interactive Skill Architect（互動式 Skill 架構師）

一個負責 **AI Agent Skill 完整生命週期**的 meta-skill：從零建立、品質健檢與優化、資安稽核，以及對自身跑行為回歸測試。它的設計目標是把「造 skill」這件事標準化——優化的目的，就是把非本工具產出的 skill 校正成與本工具產出的一致。

跨平台通用，設計上刻意不依賴「模型會自己記得規矩」：所有紀律都用可見的狀態行、進度標記、放行條件與確定性腳本來把關，讓能力較弱的模型也守得住。

---

## 三種對外模式（Phase 0 依使用者意圖路由）

| 模式 | 用途 | 觸發詞範例 | 輸出 |
|------|------|-----------|------|
| **A. 建立**（create） | 透過 Q1~Q6 結構化訪談從零打造新 skill；A1 從零／A2 以既有 skill 為藍本衍生 | 「建立 skill」「寫一個 skill」「設計新技能」 | 一個全新的 skill 資料夾 |
| **B. 優化**（optimize） | 對既有 skill 做 13 項品質診斷與修正 | 「優化 skill」「skill 健檢」「review 這個 skill」 | PASS/WARN/FAIL 診斷報告＋修正 diff |
| **C. 資安稽核**（security-audit） | 4 維度資安檢查、找惡意腳本／憑證外洩／Prompt Injection／越權外送並分級 | 「資安稽核 skill」「掃描有沒有後門／外洩」 | Critical/High/Medium/Low 風險報告 |

> **維護者工具（非使用者模式，已封存）**：另有一套「自我測試」回歸機制（`references/eval-mode.md`＋`evals/`＋`scripts/score-eval.py`／`verify-cases.py`），用來驗證本工具自身的閘門與 gotcha 有沒有退化。它**不在 Phase 0 對外路由**、不由使用者觸發，僅供維護本工具的人在改動流程檔後手動執行。

共用真相：三種對外模式共用 `references/style-guide.md`（規範本體）；建立與優化共用 `quality-checklist.md`，資安稽核獨家用 `security-checklist.md`。

> **對外產出的 skill 仍須單一職責**：本工具因同屬「Skill 生命週期管理」而例外地涵蓋多種模式；但它**產出**的 skill 必須嚴守「一個 skill 只做一類事」。

---

## 快速開始

在支援 skill 的環境（如 Claude Code / Cowork）中載入本資料夾為 skill 後，直接用自然語言表達意圖即可，例如：

- 「幫我建一個把會議逐字稿整理成紀要的 skill」→ 進入建立模式，逐題訪談。
- 「健檢 D:\path\to\some-skill」→ 進入優化模式。
- 「資安稽核 D:\path\to\some-skill」→ 進入資安稽核模式。

意圖模糊時，它會先在 Phase 0 問你要走哪個模式，不會擅自開工。

---

## 檔案結構

```
interactive-skill-architect/
├── SKILL.md                        入口：角色＋Phase 0 路由＋通用 Gotchas
├── references/                     按需載入的流程與規範
│   ├── create-mode.md              建立模式 Phase 1-4
│   ├── blueprint-intake.md         藍本入料 B0-B2（建立選 A2 後載入）
│   ├── optimize-mode.md            優化模式 Phase O1-O3
│   ├── security-audit-mode.md      資安稽核模式 Phase S1-S3
│   ├── eval-mode.md                ★維護者工具：自我測試 Phase E1-E3（非使用者模式）
│   ├── style-guide.md              規範本體 §1-§13（各模式共用）
│   ├── quality-checklist.md        13 項品質檢查
│   └── security-checklist.md       4 維度資安檢查 SEC-1~4＋風險分級
├── assets/                         輸出模板
│   ├── skill-template.md           產出新 skill 的主要骨架
│   ├── self-review-report-template.md
│   ├── optimization-report-template.md
│   ├── security-report-template.md
│   ├── eval-report-template.md     （★維護者 eval 用）
│   └── examples/                   靈感範例＋各模式報告範例
├── evals/                          ★維護者工具：本工具自身的固定行為回歸測試集
│   ├── README.md                   案例格式與撰寫鐵律
│   └── case-*.md                   14 個反向攻擊紀律的情境案例
└── scripts/                        唯讀腳本（確定性、無網路/LLM/時間相依）
    ├── _shared.py                  共用常數與評分邏輯（單一真相）
    ├── validate-skill.py           機械項驗證：編碼／命名／孤兒檔／懸空引用／體積預算
    ├── scan-security.py            資安 pattern 初篩（跨 Unix/Windows/多語言/設定檔）
    ├── score-eval.py               ★維護者 eval：機械項評分
    └── verify-cases.py             ★維護者 eval：案例元驗證（防「假綠燈」）
```

（標 ★ 者為**維護本工具自身**用的回歸測試工具，非對外使用者模式，已封存不在 Phase 0 路由。）

---

## 腳本用法

所有腳本皆唯讀、不修改任何檔案，確定性可重現：

```bash
# 對一個 skill 資料夾做機械驗證（0 = 無 FAIL）
python3 scripts/validate-skill.py <skill_dir>

# 資安 pattern 初篩（找可疑點，須人工複核）
python3 scripts/scan-security.py <skill_dir>

# 對單一 eval 案例的機械項評分
python3 scripts/score-eval.py evals/case-xxx.md <逐字稿檔>

# 案例元驗證：確認每個案例的斷言真的測到它宣稱的紀律
python3 scripts/verify-cases.py evals
```

機械檢查與語意判斷分離：可確定性判定的（編碼、命名、pattern 命中、斷言）交腳本；需理解與判斷的（是否量身打造、風險分級、步驟邏輯）交 Agent。

---

## 設計原則（節選）

- **單一真相**：命名／語氣／格式規範只在 `style-guide.md` 定義一次，各檢查清單與腳本引用它，不重抄——沒有跨檔漂移。
- **漸進揭露**：`SKILL.md` 只放路由與通用 Gotchas，各模式完整流程外置，判定模式後才載入對應一份，控制每次叫用的 context 成本。
- **Fail-closed**：任何閘門遇錯誤或不確定一律「擋」而非「放行」；檢查類腳本唯讀、遞迴走訪不跟隨 symlink、機器驗證排除二進位。
- **防呆不靠自律**：狀態行、進度標記、0 FAIL 放行門檻等可見標記是給弱模型的護欄，強制照印。
- **抵抗施壓**：使用者催促（「別問了直接做」「一次全給我」）不構成任何放行條件；對「重定義任務」型的破壞（如把「產新檔」偷換成「改藍本」），改用結構性放行條件＋寫檔前機械護欄保護原檔。

---

## 品質保證

本工具用自己的機制驗自己：

- `validate-skill.py` 對自身：**0 FAIL / 0 WARN**。
- `verify-cases.py` 對 14 個 eval 案例：**14/14 合格**（每案附 compliant＋violation 雙逐字稿，確認斷言不會假綠燈）。
- 跨模型實測（Claude Haiku 4.5，較弱模型）：**14/14 案例守住**。

新增或修改 eval 案例後，務必重跑 `verify-cases.py`；regex 一律用單反斜線（詳見 `evals/README.md` 的撰寫鐵律）。

---

## 授權

見 `LICENSE`。
