# 靈感範例：優化診斷報告

# 此檔案展示「對既有 Skill 進行健檢後產出的診斷報告」通常長什麼樣子。
# 僅供結構靈感參考，禁止原封不動套用。Agent 必須根據實際診斷結果量身調整。

---

## 診斷目標

- **Skill 名稱**：`api-docs-generator`
- **Skill 路徑**：`./api-docs-generator/`
- **診斷時間**：2026-06-10 14:30

## 目錄結構掃描結果

```
./api-docs-generator/
├── SKILL.md
├── references/
│   └── openapi-spec-guide.md
├── assets/
│   └── api-doc-template.md
└── scripts/
    └── fetch-openapi.py
```

---

## 診斷摘要

| # | 檢查項目 | 判定 | 說明 |
|---|---------|------|------|
| 1 | 觸發詞檢查 | ✅ PASS | 包含「產生 API 文件」「api docs」「寫 API 文檔」3 個觸發詞，並排除「不要用於內部 RPC 介面」 |
| 2 | Gotchas 檢查 | ⚠️ WARN | 區塊存在且有 2 條，但缺少 `<!-- 🔄 持續迭代提醒 -->` 註解 |
| 3 | 單一職責檢查 | ✅ PASS | 僅聚焦於 API 文件生成 |
| 4 | 漸進揭露檢查 | ❌ FAIL | `references/openapi-spec-guide.md` 被列在 SKILL.md 最底部的「參考資料」區塊，未綁定到具體步驟 |
| 5 | 風格規範檢查 | ⚠️ WARN | Step 3 使用了「可以考慮加入範例」的模糊語句，應改為「必須加入範例」 |
| 6 | 外部依賴品質檢查 | ✅ PASS | reference 與 template 均有實質內容 |
| 7 | 量身打造檢查 | ✅ PASS | 結構符合 Generator 模式的預期 |
| 8 | Gotchas 覆蓋率分析 | ⚠️ WARN | Step 2（解析使用者的程式碼結構）為高風險步驟但無對應 Gotcha |
| 9 | Reference 時效性分析 | ⚠️ WARN | `openapi-spec-guide.md` 中引用 OpenAPI 3.0.3，目前最新為 3.1.0。⚠️ 無法透過 WebSearch 確認，請使用者自行驗證 |
| 10 | 步驟粒度分析 | ✅ PASS | 4 個步驟粒度適中 |
| 11 | 放行條件完整性分析 | ❌ FAIL | Step 4（覆寫使用者的既有文件）無硬性放行條件，存在誤覆寫風險 |
| 12 | 腳本品質與安全分析 | ❌ FAIL | `scripts/fetch-openapi.py` 雖被 Step 1 呼叫（非孤兒），但含硬編碼絕對輸出路徑 `/Users/me/out/` 且無任何錯誤處理，命中安全紅線 |
| 13 | 步驟邏輯一致性分析 | ✅ PASS | 通讀 4 個步驟，前後指令、順序相依與編號均無矛盾 |

**整體評級**：6 項 PASS / 4 項 WARN / 3 項 FAIL（共 13 項）

---

## 詳細診斷與修正建議

### ❌ FAIL — #4 漸進揭露檢查

**問題**：`references/openapi-spec-guide.md` 集中列在 SKILL.md 最底部。

**修正建議**：將 reference 載入指令移至 Step 1：

```diff
-Step 1: 接收使用者提供的原始碼路徑或 API 端點清單。
+Step 1: 載入 `references/openapi-spec-guide.md` 取得 OpenAPI 規範標準。接收使用者提供的原始碼路徑或 API 端點清單。
```

```diff
-## 參考資料
-- references/openapi-spec-guide.md
```
（刪除底部的集中列表）

---

### ❌ FAIL — #11 放行條件完整性分析

**問題**：Step 4 會覆寫使用者的既有 API 文件，但沒有設置硬性放行條件。

**修正建議**：

```diff
 Step 4: 將生成的文件寫入指定路徑。
+  - **放行條件**：必須先向使用者展示完整預覽，獲得明確確認後才可覆寫既有檔案。禁止靜默覆寫。
```

---

### ❌ FAIL — #12 腳本品質與安全分析

**問題**：`scripts/fetch-openapi.py` 含硬編碼的絕對輸出路徑，換一台機器即失效，且無錯誤處理（網路失敗時靜默產出空檔）。

**修正建議**：輸出路徑改為參數、加入基本錯誤處理：

```diff
-OUT_DIR = "/Users/me/out/"
+import sys
+OUT_DIR = sys.argv[1] if len(sys.argv) > 1 else "./out/"
```

```diff
-resp = requests.get(url)
-spec = resp.json()
+resp = requests.get(url, timeout=30)
+resp.raise_for_status()
+spec = resp.json()
```

並在 SKILL.md 呼叫該腳本的步驟旁補上輸入/輸出契約說明（參數、退出碼）。

---

### ⚠️ WARN — #2 Gotchas 檢查

**問題**：缺少持續迭代提醒註解。

**修正建議**：在 Gotchas 區塊底部補充：

```diff
+<!-- 🔄 持續迭代提醒：每次 Agent 執行此技能犯錯時，請回來補充新的 Gotcha。 -->
```

---

### ⚠️ WARN — #5 風格規範檢查

**問題**：Step 3 使用了模糊語句「可以考慮加入範例」。

**修正建議**：

```diff
-Step 3: 根據解析結果填入模板。可以考慮加入請求/回應範例。
+Step 3: 根據解析結果填入模板。必須為每個端點加入請求/回應範例。
```

---

### ⚠️ WARN — #8 Gotchas 覆蓋率分析

**問題**：Step 2（解析使用者的程式碼結構）為高風險步驟，若解析失敗可能導致後續步驟產出錯誤的文件，但無對應 Gotcha。

**修正建議**：新增 Gotcha：

```diff
+- **解析失敗的靜默降級**：當程式碼解析器無法辨識特定的函數簽名或型別註解時，Agent 容易靜默跳過該端點。必須對每個解析失敗的端點產出明確的警告標記，禁止靜默忽略。
```

---

### ⚠️ WARN — #9 Reference 時效性分析

**問題**：`openapi-spec-guide.md` 中引用 OpenAPI 3.0.3，可能已有更新版本。

**標註提醒**：⚠️ 此項無法透過自動工具確認，請使用者前往 [OpenAPI 官方網站](https://spec.openapis.org/) 確認目前最新版本，並視需要更新 reference 文件。
