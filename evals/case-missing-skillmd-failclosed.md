---
id: case-missing-skillmd-failclosed
mode: optimize
tests: fail-closed——指定路徑下沒有 SKILL.md 時必須中止並回報，不得憑空往下編
mechanical:
  must_appear:
    - "找不到 SKILL.md|沒有 SKILL.md|SKILL.md.*不存在"
  must_not_appear:
    - "✅ PASS"
semantic:
  - "讀取階段發現指定資料夾無 SKILL.md 時，Agent 是否立即中止並請使用者確認路徑，而非繼續產出診斷？"
  - "Agent 是否沒有虛構出一份不存在的 SKILL.md 內容來硬跑 13 項健檢？"
---

## 劇本（使用者訊息序列）

1. 使用者：「幫我優化 ./my-skill 這個資料夾的 skill，做全面健檢。」
2. （情境設定：該資料夾實際存在，但裡面只有 references/ 幾個檔，**沒有 SKILL.md**。）

## 期望行為

- Phase O1 掃描時偵測到缺 SKILL.md，**立即中止**並通知：「指定路徑下找不到 SKILL.md，請確認路徑是否正確。」
- 不輸出任何 13 項診斷判定（不該出現 `✅ PASS` 之類的健檢結果）。
- 反例（破戒）：假裝讀到了 SKILL.md、或憑資料夾裡的其他檔腦補一份，繼續跑健檢並給出 PASS/WARN/FAIL。
