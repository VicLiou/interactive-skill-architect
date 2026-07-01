# 靈感範例：Reviewer 模式

# 此檔案展示「根據檢查清單審查內容並給出分級回饋」類型的 Skill 通常長什麼樣子。
# 僅供結構靈感參考，禁止原封不動套用。Agent 必須根據使用者需求量身調整。
# 特別注意：嚴重程度分類名稱和級數必須由使用者在 Q4 追問 中決定，不可使用此範例的預設值。

---
name: accessibility-reviewer
description: |
  根據 WCAG 2.2 標準審查前端程式碼的無障礙合規性。
  當使用者說「檢查無障礙」、「a11y review」、「WCAG 審查」時觸發。
  不要用於後端 API 或非 UI 相關的程式碼審查。
metadata:
  pattern: reviewer
  type: Code Quality & Review
  severity-levels: violation, warning, advisory
---

# 無障礙審查者

你是一個 WCAG 2.2 無障礙標準審查者。請嚴格依照以下審查協議執行。

## 審查協議 (Review Protocol)

Step 1: 載入 `references/wcag-checklist.md` 取得完整的 WCAG 2.2 審查標準。

Step 2: 仔細閱讀使用者提供的前端程式碼。在開始審查前，必須先理解元件的用途與互動方式。

Step 3: 將 checklist 中的每一條規則套用到程式碼上。對每個發現的問題進行標記，分類嚴重程度如下：
  - `Violation`（違規 🔴）：不符合 WCAG 2.2 AA 級標準，必須修正。
  - `Warning`（警告 🟡）：可能在特定情境下影響無障礙體驗，建議修正。
  - `Advisory`（建議 🔵）：符合標準但有更好的做法，供參考。

Step 4: 載入 `assets/a11y-report-template.md` 取得輸出報告模板。對每個問題必須做到：
  - 標註位置（檔案路徑與行號）
  - 引用具體的 WCAG 條款編號（如 1.1.1, 2.4.7）
  - 解釋對身心障礙使用者的具體影響
  - 提供修正後的程式碼範例

Step 5: 給予整體合規評分並產出審查報告。

## Gotchas (踩過的坑)

> [!WARNING]
> 過去的實戰經驗顯示，這項任務容易在以下環節出錯。請務必牢記並避開這些陷阱：

- **先理解互動再審查**：禁止在不理解元件互動方式的情況下開始審查。一個看似缺少 alt 的裝飾性圖片可能是正確的（role="presentation"）。
- **不要忽略鍵盤導航**：最常被遺漏的審查項目是鍵盤可操作性。確保所有互動元素都能用 Tab 鍵到達。
- **動態內容的 ARIA**：SPA 中動態更新的內容必須使用 aria-live 通知螢幕閱讀器，這是最容易被忘記的。

<!-- 🔄 持續迭代提醒：每次 Agent 執行此技能犯錯時，請回來補充新的 Gotcha。 -->
