# 靈感範例：Pipeline 模式

# 此檔案展示「多步驟流水線，每步有硬性放行條件」類型的 Skill 通常長什麼樣子。
# 僅供結構靈感參考，禁止原封不動套用。Agent 必須根據使用者需求量身調整。
# 特別注意：步驟數量、放行條件與最終步驟的內容必須由使用者在 Q4／Q4 追問 中決定，不可使用此範例的預設值。

---
name: api-release-pipeline
description: |
  執行 API 上線前的多階段檢查流水線，確保每個放行條件都滿足後才進入下一階段。
  當使用者說「跑上線流程」、「API release checklist」、「準備發版」時觸發。
  不要用於前端發版、資料庫 migration 或非 API 的發版流程。
metadata:
  pattern: pipeline
  type: CI/CD & Deployment
  steps: "5"
---

# API 發版流水線

你正在執行一條 API 發版流水線。請依序執行每個步驟，**禁止**跳過任何步驟。若任何步驟失敗或未獲使用者確認，禁止進入下一步。

## Step 1 — 版本號確認
確認本次發版的版本號、變更日誌 (Changelog) 與影響範圍。
- **放行條件**：使用者明確確認版本號與 Changelog 內容正確。

## Step 2 — API 合約驗證
載入 `references/api-contract.yaml` 取得 OpenAPI 規格。比對本次變更是否有 breaking change。
- **放行條件**：無 breaking change，或 breaking change 已記錄在 migration guide 中。

## Step 3 — 測試覆蓋檢查
確認所有新增或修改的 endpoint 都有對應的整合測試，且測試通過率 100%。
- **放行條件**：測試全數通過，且覆蓋率不低於門檻值。

## Step 4 — 安全掃描
載入 `references/security-checklist.md` 執行安全審查：認證、授權、輸入驗證、速率限制。
- **放行條件**：無 Critical 或 High 風險項目。

## Step 5 — 最終確認與部署
彙整 Step 1~4 的結果，產出發版摘要報告。載入 `assets/release-summary-template.md` 填寫報告。
- **放行條件**：使用者最終確認「同意發版」。

## Gotchas (踩過的坑)

> [!WARNING]
> 過去的實戰經驗顯示，這項任務容易在以下環節出錯。請務必牢記並避開這些陷阱：

- **禁止跳級**：即使你認為某步驟結果很明顯，也必須走完流程並取得使用者確認。
- **分段載入**：不同步驟需要的 references 和 assets 請在該步驟才載入，禁止一開始全部塞進 context。
- **Breaking change 的定義**：不只是刪除欄位。修改回傳型別、新增必填參數、改變錯誤碼也都算 breaking change。

<!-- 🔄 持續迭代提醒：每次 Agent 執行此技能犯錯時，請回來補充新的 Gotcha。 -->
