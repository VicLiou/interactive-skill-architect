---
id: case-q4-dynamic-followup
mode: create
tests: 跳過動態追問——Q2 描述 reviewer 型 skill 時，Q4 必須追問嚴重程度分級，不得略過就進產出
mechanical:
  must_appear:
    - "嚴重程度|分級|Blocker|等級"
semantic:
  - "使用者在 Q2 描述了 reviewer/審查型運作方式後，Agent 是否在 Q4 追問嚴重程度分級（分幾級、各級名稱與定義）？"
  - "Agent 是否沒有因為『運作方式聽起來懂了』就跳過動態追問、直接進入產出？"
---

## 劇本（使用者訊息序列）

1. 使用者：「建一個 skill，觸發詞『審查我的 SQL』。運作方式是：使用者貼 SQL，它照檢查清單逐條審查、對每個問題給出回饋。」
2. （Agent 走到 Q4 執行步驟與硬性閘門，並依 Q2 的 reviewer 描述觸發追問）

## 期望行為

- 辨識出 Q2 屬 reviewer 型，Q4 **必須動態追問**：嚴重程度分幾級？各級名稱與定義？（例如 Blocker/Warning/Nit 或 Critical/High/Medium/Low）。
- 不因「運作方式已清楚」就跳過追問直接產出——分級是 reviewer 型 skill 的關鍵未知參數。
- 反例（破戒）：問完 Q4 主問題就說「資訊夠了，直接進入產出」，沒追問嚴重程度分級。

## 逐字稿・compliant（元驗證：應全數 PASS）
```compliant
【建立模式・Phase 2】追問（不計入進度）：您的審查回饋想分幾個嚴重程度等級？各級的名稱與定義是什麼？例如 Blocker/Warning/Nit，或 Critical/High/Medium/Low。
```

## 逐字稿・violation（元驗證：應至少一項 FAIL）
```violation
【建立模式・Phase 2】好，運作方式我懂了，資訊也夠了，我直接進入 Phase 3 產出這個 skill。
```
