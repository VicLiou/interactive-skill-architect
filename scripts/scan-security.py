#!/usr/bin/env python3
"""
scan-security.py — 對一個 Skill 資料夾做「確定性」的資安 pattern 初篩（唯讀，不修改任何檔案）。

用法:
    python3 scan-security.py <skill_dir>     # 省略則掃當前目錄

退出碼: 0 = 無命中且無待人工複核項；1 = 有命中或有待複核項；2 = 執行錯誤（如路徑不存在）。

定位: 這是資安稽核模式 Phase S1 的「確定性初篩」，只負責用 regex 找出可疑點，
      對應 references/security-checklist.md 的 4 維度（SEC-1~SEC-4）。
      不取代 Phase S2 的語意複核——會有誤報與漏報，每個命中都須由 Agent 語意確認，
      風險分級（Critical/High/Medium/Low）也由 Agent 依 checklist 的判斷紀律裁定。

覆蓋範圍:
  - 遞迴掃描整個資料夾，不假設 references/assets/scripts 慣例、且含隱藏檔
    （用 os.walk 而非 glob，因 glob 會跳過 dotfile）。
  - .git 內部原則上略過，但仍納入 .git/hooks/*（非 .sample）與 .git/config
    （git hooks 與 core.hookspath/sshCommand 會自動執行，屬供應鏈攻擊面）。
  - 編碼強健：自動處理 UTF-8/UTF-16(BOM 或無 BOM)/latin-1，避免 UTF-16 的
    PowerShell 腳本因解碼錯誤而整個逃過掃描。
  - 平台/語言：Unix shell、Windows(PowerShell/cmd/LOLBins)、多語言 runtime、
    設定檔宣告的自動執行（MCP command / hooks）。
  - 二進位以內容嗅探為主、副檔名為輔判定（防改名繞過），無法內容掃描但會**輸出 SHA256 指紋**供外部比對；
    symlink 只記錄指向、不讀其內容（避免被誘導讀到資料夾外機敏檔）；檔數達 MAX_FILES 上限即截斷（DoS 自保）。
  - 已知限制（見檔尾與 security-audit-mode.md Gotchas）：逐行比對，無法偵測
    跨行拆分／整段編碼混淆的 payload；二進位內容本身無法掃描（僅出指紋）。

由 interactive-skill-architect 的資安稽核模式（Phase S1 初篩／Phase S3 回歸掃描）呼叫；
環境無法執行時退回人工逐檔審。

降噪：對「命中密度極高且橫跨多維度」的檔（多為資安 checklist／掃描規則／稽核報告等
      描述而非執行危險行為的自指涉文件），改為整檔聚合一行提示而非逐條列印，交人工整檔
      判讀。此為顯示形態調整——總命中數、退出碼、待複核旗標皆不變，不遺漏任何命中。
"""
import sys, os, re
sys.dont_write_bytecode = True   # 唯讀承諾（§13.2）：禁止 import 產生 __pycache__，須在 import _shared 之前設定
from _shared import BINARY_EXTS, is_binary, sha256_of, MAX_BYTES, MAX_FILES   # 單一真相

# (維度, 規則名, 正規表達式, 初判提示, 是否忽略大小寫)。
# 初判僅供參考，最終分級由 Agent 依 checklist 裁定。
# 命令規則多設 ci=True（Windows/PowerShell 大小寫不敏感）；密鑰前綴設 ci=False。
RULES = [
    # ---------- SEC-1 惡意/危險腳本 ----------
    ("SEC-1", "遠端執行管線 curl|sh (Unix)", r"(curl|wget)\b[^\n|]*\|\s*(sudo\s+)?(ba|z|k)?sh\b", "Critical", True),
    ("SEC-1", "process substitution 執行 (Unix)", r"(source|\.)\s+<\(\s*(curl|wget)", "Critical", True),
    ("SEC-1", "PowerShell 下載後執行 IEX/DownloadString", r"(iex|invoke-expression)\b.*(downloadstring|net\.webclient|invoke-webrequest|iwr|invoke-restmethod|irm)|download(string|file)\s*\(", "Critical", True),
    ("SEC-1", "PowerShell 編碼/隱藏執行", r"-e(nc(odedcommand)?)?\s+[A-Za-z0-9+/=]{20,}|frombase64string|-nop\b|-w(indowstyle)?\s+hidden|-exec(utionpolicy)?\s+bypass|set-executionpolicy\s+bypass", "Critical", True),
    ("SEC-1", "Windows 下載工具 certutil/bitsadmin", r"certutil\b[^\n]*(-urlcache|-f\b)|bitsadmin\b[^\n]*/transfer", "Critical", True),
    ("SEC-1", "Windows 腳本執行器 mshta/rundll32/regsvr32/wscript", r"\b(mshta|rundll32|regsvr32|wscript|cscript)\b", "High", True),
    ("SEC-1", "反向/繫結 shell", r"/dev/tcp/|n(c|cat)\s+-e|socat\b[^\n]*exec|bash\s+-i\s*>&", "Critical", True),
    ("SEC-1", "混淆執行 eval/atob/base64/fromCharCode/hex", r"eval\s*\(\s*atob|base64\s+-d[^\n]*\|\s*(ba)?sh|string\.fromcharcode|fromcharcode|\[char\]|(\\x[0-9a-f]{2}){6,}", "Critical", True),
    ("SEC-1", "破壞性命令 rm -rf/dd/mkfs/shred (Unix)", r"\brm\s+-[a-z]*rf?[a-z]*\b|\bdd\s+of=/dev/|\bmkfs\b|chmod\s+-R\s+0*777|\bshred\b", "High", True),
    ("SEC-1", "破壞性命令 del/rmdir/format/cipher (Windows)", r"\bdel\s+/[a-z/ ]*[fsq]|\br(m)?dir\s+/s|\bformat\s+[a-z]:|cipher\s+/w|remove-item\b[^\n]*-recurse[^\n]*-force", "High", True),
    ("SEC-1", "fork bomb", r":\(\)\s*\{\s*:\|:&\s*\}", "High", False),
    ("SEC-1", "提權 sudo/runas", r"(?<![-\w])sudo\s+|\brunas\b|start-process\b[^\n]*-verb\s+runas", "High", True),
    ("SEC-1", "持久化 cron/schtasks/registry Run/service", r"\bcrontab\s+-|schtasks\s+/create|register-scheduledtask|new-service\b|reg\s+add\b[^\n]*\\run|currentversion\\run", "High", True),
    ("SEC-1", "跨語言命令執行 os.system/subprocess/exec/system", r"os\.system\s*\(|subprocess\.[a-z]+\([^\n]*shell\s*=\s*true|\bexec\s*\(|require\(\s*['\"]child_process|child_process|shell_exec\s*\(|passthru\s*\(|\bsystem\s*\(", "High", True),
    ("SEC-1", "不安全反序列化 pickle/yaml.load/marshal", r"pickle\.loads?\s*\(|yaml\.load\s*\((?![^)]*safe)|marshal\.loads?\s*\(", "High", True),
    ("SEC-1", "停用資安防護 (Defender/防火牆/SELinux)", r"set-mppreference\b[^\n]*-disable|add-mppreference\b[^\n]*-exclusion|iptables\s+-f\b|ufw\s+disable|setenforce\s+0", "High", True),

    # ---------- SEC-2 憑證與敏感資料 ----------
    ("SEC-2", "私鑰區塊", r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----", "High", False),
    ("SEC-2", "AWS Access Key", r"\bAKIA[0-9A-Z]{16}\b", "High", False),
    ("SEC-2", "GitHub Token", r"\bgh[pousr]_[0-9A-Za-z]{30,}\b", "High", False),
    ("SEC-2", "Slack Token", r"\bxox[baprs]-[0-9A-Za-z-]{10,}\b", "High", False),
    ("SEC-2", "Google API Key", r"\bAIza[0-9A-Za-z_\-]{35}\b", "High", False),
    ("SEC-2", "Stripe 私有金鑰", r"\bsk_live_[0-9A-Za-z]{16,}\b", "High", False),
    ("SEC-2", "其他 API 金鑰 (OpenAI/Anthropic/SendGrid/npm/Twilio)", r"\bsk-ant-[0-9A-Za-z_\-]{20,}|\bsk-[A-Za-z0-9]{20,}\b|\bSG\.[0-9A-Za-z_\-]{16,}|\bnpm_[0-9A-Za-z]{30,}|\bAC[0-9a-f]{32}\b", "High", False),
    ("SEC-2", "硬編碼密鑰/token", r"(api[_-]?key|secret|token|password|passwd|access[_-]?key)\s*[:=]\s*['\"][^'\"]{8,}['\"]", "High", True),
    ("SEC-2", "讀取敏感路徑 (Unix)", r"~/\.ssh|~/\.aws|/etc/(passwd|shadow)|\.aws/credentials|/\.docker/config|keychain", "Medium", True),
    ("SEC-2", "讀取敏感路徑/憑證 (Windows)", r"%userprofile%\\\.ssh|%appdata%|get-credential|\bcmdkey\b|protecteddata|vaultcmd|\bmimikatz\b", "Medium", True),
    ("SEC-2", "雲端/容器憑證讀取", r"aws\s+configure\s+get|aws\s+sts\s+|gcloud\s+auth\s+print|az\s+account\s+get-access-token|kubectl\s+config\s+view|docker\s+login\b", "Medium", True),
    ("SEC-2", "本機隱私擷取 (剪貼簿/截圖/瀏覽器憑證)", r"get-clipboard|pbpaste|xclip\s+-o|screencapture|logins\.json|cookies\.sqlite|Login Data", "Medium", True),
    ("SEC-2", "環境變數/檔案外送", r"(env|printenv|get-content[^\n]*)\|[^\n]*(curl|wget|nc|invoke-restmethod|irm)[^\n]*https?://|curl[^\n]*-d\s*@|upload(string|data)|invoke-restmethod\b[^\n]*-method\s+post", "Critical", True),
    ("SEC-2", "可疑外送通道 (webhook/paste/tunnel/scp/DNS)", r"hooks\.slack\.com|discord(app)?\.com/api/webhooks|api\.telegram\.org/bot|pastebin\.com/api|transfer\.sh|0x0\.st|[a-z0-9]+\.ngrok\.io|\bscp\s+[^\n]*@|\brsync\s+[^\n]*::|nslookup\s+[^\n]*\$|\bdig\s+[^\n]*\$", "High", True),
    ("SEC-2", "雲端中繼資料 SSRF", r"169\.254\.169\.254|metadata\.google\.internal", "High", True),
    ("SEC-2", "疑似編碼 blob（須人工解碼複核）", r"[A-Za-z0-9+/]{200,}={0,2}", "Low", False),

    # ---------- SEC-3 Prompt Injection（掃所有文字檔的自然語言指令） ----------
    ("SEC-3", "繞過安全機制指令", r"(忽略|無視|略過|跳過)(先前|前面|上述|以上|所有).{0,6}(指令|指示|規則|限制)|(停用|關閉|繞過|解除).{0,10}(安全|檢查|防護|放行|限制|guard)|ignore\s+(all\s+)?previous\s+instructions|disable\s+(the\s+)?(safety|security|guard)|override\s+(the\s+)?(safety|security)", "Critical", True),
    ("SEC-3", "對使用者隱瞞指令", r"不要(告訴|讓|向|對).{0,6}使用者|不(得|要)(記錄|顯示|提及|告知)|(靜默|悄悄|暗中|偷偷).{0,4}(執行|完成|上傳|傳送)|隱藏(此|這|該).{0,4}(步驟|操作|指令)|do\s+not\s+(tell|inform|mention|log|show).{0,20}(user|this)|without\s+(telling|informing|notifying)", "Critical", True),
    ("SEC-3", "抓取後照做未受信任內容", r"(fetch|下載|讀取|抓取).{0,20}(url|網址|連結).{0,20}(照|依|按|遵循|follow).{0,6}(指令|instruction)|follow\s+the\s+instructions\s+(in|at|from)", "High", True),
    ("SEC-3", "隱藏/雙向覆寫字元 (zero-width/Trojan Source)", r"[​‌‍⁠‪-‮]", "High", False),

    # ---------- SEC-4 權限與外部呼叫 ----------
    ("SEC-4", "下載可執行物（須確認有無 hash/簽章校驗）", r"(curl|wget|invoke-webrequest|iwr|invoke-restmethod|irm)\b[^\n]*\.(exe|msi|dll|sh|ps1|bat|cmd|scr|jar|whl|pkg|dmg|deb|rpm)\b|(-o|-outfile|--output)\s+\S*\.(exe|msi|dll|sh|ps1|bat|cmd|scr|jar|whl|pkg|dmg|deb|rpm)\b", "Low", True),
    ("SEC-4", "命令注入傾向 eval/sh -c/IEX 帶變數", r"eval\s+[\"']?\$|sh\s+-c\s+[\"'][^\"']*\$|invoke-expression\b[^\n]*\$", "High", True),
    ("SEC-4", "設定檔宣告自動執行 (MCP command/hooks/git hookspath)", r"\"command\"\s*:\s*\[?\s*\"|core\.hookspath|core\.fsmonitor|sshcommand\s*=|\"(pre|post)tooluse\"\s*:|\"hooks\"\s*:", "Medium", True),
    ("SEC-4", "frontmatter 過度授權 allowed-tools", r"allowed-tools\s*:.*(\*|bash)", "Medium", True),
    ("SEC-4", "未鎖版相依安裝 (跨生態)", r"pip\s+install\s+(?!.*==)[a-zA-Z]|npm\s+i(nstall)?\s+(?!.*@)[a-zA-Z]|(choco|winget|nuget)\s+install|install-(module|package)|gem\s+install|go\s+install\b", "Low", True),
]

COMPILED = [(dim, name, re.compile(pat, re.IGNORECASE if ci else 0), hint)
            for (dim, name, pat, hint, ci) in RULES]

def read_text(p):
    """編碼強健讀檔：處理 UTF-8 / UTF-16(BOM 或無 BOM) / latin-1，
    避免 UTF-16 的 PowerShell 腳本因 utf-8 解碼失敗而整個逃過掃描。"""
    try:
        raw = open(p, "rb").read(MAX_BYTES)
    except Exception:
        return None
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        try:
            return raw.decode("utf-16")
        except Exception:
            pass
    # 無 BOM 的 UTF-16（null 密度高）：必須「先於」utf-8 嘗試——否則 ASCII 的 UTF-16
    # 會被 utf-8 成功解成夾雜 NUL 的亂碼字串（NUL 是合法 utf-8 碼位），使 pattern 全數掃不到而漏報。
    if raw.count(b"\x00") > len(raw) // 4:
        for enc in ("utf-16-le", "utf-16-be", "utf-16"):
            try:
                return raw.decode(enc)
            except Exception:
                pass
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        pass
    return raw.decode("latin-1")                     # 不會失敗，保留 ASCII pattern


def collect_files(target):
    """遞迴收集檔案；.git 只納入 hooks(非 .sample) 與 config，其餘略過。

    安全設計（style-guide §13.3）：
      - symlink **不讀取其內容**，只記錄連結與指向路徑（避免被誘導讀到資料夾外的機敏檔）；
      - 二進位以內容嗅探為主、副檔名為輔判定（防改名繞過），並計算 SHA256 供身分驗證/掉包偵測；
      - os.walk 預設 followlinks=False，不遞迴進 symlink 指向的目錄；
      - 檔數上限 MAX_FILES，避免超深/超大樹造成 DoS。
    """
    files, skipped_bin, symlinks, truncated = [], [], [], [False]

    def add(p):
        rel = os.path.relpath(p, target).replace(os.sep, "/")
        if os.path.islink(p):                       # symlink：只記錄、不讀內容
            try:
                tgt = os.readlink(p)
            except OSError:
                tgt = "?"
            symlinks.append((rel, tgt))
            return
        if is_binary(p):                            # 內容嗅探為主、副檔名為輔
            skipped_bin.append((rel, sha256_of(p)))
        else:
            files.append((p, rel))

    for root, dirs, fnames in os.walk(target):
        dirs[:] = [d for d in dirs if d != ".git"]
        for fn in fnames:
            if len(files) + len(skipped_bin) >= MAX_FILES:
                truncated[0] = True
                break
            add(os.path.join(root, fn))
        if truncated[0]:
            break

    # 額外納入 .git 的自動執行面（hooks 與 config）
    git_dir = os.path.join(target, ".git")
    cfg = os.path.join(git_dir, "config")
    if os.path.isfile(cfg):
        add(cfg)
    hooks = os.path.join(git_dir, "hooks")
    if os.path.isdir(hooks):
        for fn in os.listdir(hooks):
            fp = os.path.join(hooks, fn)
            if os.path.isfile(fp) and not fn.endswith(".sample"):
                add(fp)
    return files, skipped_bin, symlinks, truncated[0]


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    if not os.path.isdir(target):
        print("ERROR: 路徑不存在或非資料夾: " + target)
        return 2

    files, skipped_bin, symlinks, truncated = collect_files(target)

    hits = []  # (dim, rule, hint, rel, lineno, line)
    for p, rel in files:
        text = read_text(p)
        if text is None:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            for dim, name, rx, hint in COMPILED:
                if rx.search(line):
                    hits.append((dim, name, hint, rel, i, line.strip()[:120]))

    print("== scan-security 資安 pattern 初篩報告 ==")
    print("（已遞迴掃描 " + str(len(files)) + " 個文字檔，含隱藏檔/.git hooks；編碼強健；涵蓋 Unix/Windows/多語言/設定檔）")
    print("（決定性初篩，非最終判定；每項須由 Agent 依 security-checklist.md 語意複核與分級）\n")

    need_review = bool(skipped_bin or symlinks or truncated)
    if truncated:
        print("⚠ 檔案數達上限 " + str(MAX_FILES) + "，掃描已截斷（資源上限保護）；請分區重掃或人工確認剩餘檔案。\n")
    if skipped_bin:
        print("⚠ 無法掃描的二進位檔（含 SHA256 指紋；須人工確認用途/來源，並拿 hash 去外部比對 VirusTotal／廠商公布值／Authenticode）：")
        for rel, digest in skipped_bin:
            print("    " + rel + "  sha256=" + (digest or "?"))
        print("")
    if symlinks:
        print("⚠ 偵測到符號連結（未讀取其內容；須人工確認指向是否逃逸資料夾外）：")
        for rel, tgt in symlinks:
            print("    " + rel + "  ->  " + tgt)
        print("")

    if not hits:
        print("未命中任何可疑 pattern。仍須 Agent 完成 SEC-1~SEC-4 語意複核（尤其 SEC-3 文本注入與整段編碼混淆，掃描器可能漏報）。")
        return 1 if need_review else 0

    # 降噪（不降敏）：資安文件本身（checklist、掃描規則、稽核報告）必然大量「自命中」——
    # 它們**描述**危險 pattern 而非**執行**。逐條列印會淹沒真正的訊號。
    # 對「命中密度極高且橫跨多維度」的檔，改為整檔聚合一行提示，交人工整檔判讀。
    # 這只改變「顯示形態」：總命中數、exit code、need_review 全部不變，不遺漏任何命中。
    # 門檻刻意訂高（避免把真 payload 檔誤收），且聚合檔仍明確要求人工整檔閱讀。
    DENSE_MIN_HITS, DENSE_MIN_DIMS = 15, 3
    per_file = {}
    for h in hits:
        per_file.setdefault(h[3], []).append(h)
    dense = {rel: hs for rel, hs in per_file.items()
             if len(hs) >= DENSE_MIN_HITS and len({x[0] for x in hs}) >= DENSE_MIN_DIMS}

    if dense:
        print("⚠ 高密度命中檔（命中數多且橫跨多維度，疑為資安文件／pattern 定義／稽核報告）：")
        print("    這類檔通常在「描述」而非「執行」危險行為，屬預期的自命中；已聚合，請**整檔人工判讀**確認無真實 payload。")
        for rel in sorted(dense):
            hs = dense[rel]
            dims = ",".join(sorted({x[0] for x in hs}))
            print("    " + rel + "  （" + str(len(hs)) + " 命中，橫跨 " + dims + "）")
        print("")

    for dim in ("SEC-1", "SEC-2", "SEC-3", "SEC-4"):
        dh = [h for h in hits if h[0] == dim and h[3] not in dense]
        if not dh:
            continue
        print("[" + dim + "] " + str(len(dh)) + " 命中（不含高密度聚合檔）")
        for _, name, hint, rel, ln, txt in dh:
            print("  - (" + hint + ") " + name + " @ " + rel + ":" + str(ln))
            print("      " + txt)

    dense_hits = sum(len(hs) for hs in dense.values())
    tail = "" if not dense else ("（其中 " + str(dense_hits) + " 個來自 " + str(len(dense)) + " 個高密度聚合檔，見上）")
    print("\n-- 共 " + str(len(hits)) + " 個可疑命中" + tail + "；初判提示僅供參考，最終分級由 Agent 裁定 --")
    return 1


if __name__ == "__main__":
    sys.exit(main())
