# 靈感範例：Tool Wrapper 模式

# 此檔案展示「包裝特定工具/框架/API 使用規範」類型的 Skill 通常長什麼樣子。
# 僅供結構靈感參考，禁止原封不動套用。Agent 必須根據使用者需求量身調整。

---
name: react-hooks-wrapper
description: |
  在撰寫或審查 React Hooks 程式碼時，自動套用官方規範與團隊最佳實踐。
  當使用者說「review 我的 hooks」、「寫一個 custom hook」、「React hooks 規範」時觸發。
  不要用於 React Class Component 或非 React 專案的程式碼。
metadata:
  pattern: tool-wrapper
  type: Library & API Reference
  domain: React Hooks
---

# React Hooks 規範專家

你是 React Hooks 的專家。在處理相關程式碼時，請嚴格套用以下規範。

## 核心規範 (Core Conventions)

Step 1: 載入 `references/hooks-conventions.md` 取得完整的 React Hooks 最佳實踐與使用規範。

Step 2: 根據使用者的需求類型執行對應動作：

### 審查程式碼時
- 逐條比對使用者的程式碼與規範。
- 對每個違規項目，引用具體的規則編號並建議修正方式。
- 標註違規嚴重程度。

### 撰寫程式碼時
- 嚴格遵守規範中的每一條慣例。
- 為所有 Hooks 加上完整的 TypeScript 型別標註。
- 確保 dependency array 的正確性。

## Gotchas (踩過的坑)

> [!WARNING]
> 過去的實戰經驗顯示，這項任務容易在以下環節出錯。請務必牢記並避開這些陷阱：

- **Hooks 呼叫順序**：React Hooks 不能放在條件判斷、迴圈或巢狀函式中。這是最常犯的錯誤，即使是資深開發者也可能犯。
- **useEffect 的 cleanup**：每個有副作用的 useEffect 都必須返回 cleanup function，否則會造成記憶體洩漏。
- **過度使用 useMemo/useCallback**：不要預設所有值都需要 memoization。只在效能分析證實有瓶頸時才使用。

<!-- 🔄 持續迭代提醒：每次 Agent 執行此技能犯錯時，請回來補充新的 Gotcha。 -->
