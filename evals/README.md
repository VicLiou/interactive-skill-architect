# evals/ — 本 skill 的行為回歸測試集

這裡是 `interactive-skill-architect` **自己的**固定測試題庫，供**自我測試模式（Phase 0 選 D）**使用。
被測物是本 skill 的**行為**（狀態機、硬性閘門、gotcha 有沒有被守住），不是使用者的 skill。

## 設計原則

- **每個案例＝反向攻擊一條紀律**：把 skill 裡一條硬性閘門或 gotcha 反過來，寫一個會誘使模型破戒的情境，看它守不守得住。
- **固定資產、不現生**：案例是版控的固定題庫。回歸測試靠「每次用同一批題目」才能比較分數；禁止每次跑才臨時生成。
- **機械 vs 語意分界**：`mechanical` 由 `scripts/score-eval.py` 確定性判定；`semantic` 由 judge 依逐字稿判斷。

## 案例檔格式

每個 `case-*.md` 的 frontmatter：

```yaml
---
id: case-xxx
mode: create | optimize | security
tests: 一句話說明測哪條紀律
mechanical:
  must_appear:        # regex，必須在逐字稿出現
    - "..."
  must_not_appear:    # regex，必須不出現
    - "..."
  ordering:           # 選用，片語須依序出現
    - ["先", "後"]
semantic:             # judge 判斷題
  - "..."
---
## 劇本（使用者訊息序列）
## 期望行為
```

## 如何跑

在本資料夾開 session，說「跑 evals」「自我測試」「回歸測試」即觸發自我測試模式。
機械項評分：`python3 scripts/score-eval.py evals/case-xxx.md <逐字稿檔>`。

## 維護

真實使用中本 skill 犯了新錯 → 把那次失敗轉寫成一個新的 `case-*.md` 補進來（自我測試模式 E3 選 C）。
測試集隨 skill 一起長大；每個真實 bug 都變成一個永久回歸案例。
