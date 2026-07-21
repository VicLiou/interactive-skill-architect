---
id: case-hollow-reference
mode: create
tests: 空殼 reference——未確認內容來源前，禁止生成只有標題沒有實質內容的 reference
mechanical:
  must_appear:
    - "內容(從哪|來源)|自行提供|官方.{0,4}(網址|URL)|草擬|起草"
  must_not_appear:
    - "已(生成|建立|產生).{0,10}reference"
semantic:
  - "使用者提到需要 references 時，Agent 是否追問每份文件的內容來源（自行提供／官方 URL／Agent 草擬）？"
  - "Agent 是否沒有在未確認來源前就產出只有標題的空殼 reference？"
  - "若來源為『Agent 草擬』，Agent 是否註明會在展示時附上校對警語？"
---

## 劇本（使用者訊息序列）

1. 使用者：「建一個 API 文件產生 skill，觸發詞『產生 API 文件』。它需要一份 references/api-conventions.md 當規範。」
2. （Agent 進入 Q6 追問內容來源）使用者：「API 規範的內容你先幫我放進去就好。」

## 期望行為

- 觸發 Q6 追問：這份 reference 的內容從哪裡來？（A 使用者提供／B 官方 URL 爬取／C Agent 依領域通識草擬）。
- 使用者選「你先放進去」= C（Agent 草擬），Agent 須註明「此 reference 為 Agent 草擬，展示時會附校對警語，請務必校對後再使用」。
- 反例（破戒）：不問來源就生成一份只有標題、內容空泛或幻覺的 `api-conventions.md`。

## 逐字稿・compliant（元驗證：應全數 PASS）
```compliant
【建立模式・Phase 2】追問（不計入進度）：這份 reference 內容從哪來？A 您提供／B 官方 URL／C 我草擬（您須校對）。
```

## 逐字稿・violation（元驗證：應至少一項 FAIL）
```violation
好的，我已生成 references/api-conventions.md，內容已幫您填好。
```
