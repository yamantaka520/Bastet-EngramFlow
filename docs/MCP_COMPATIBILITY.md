# MCP 相容性策略

## 1. 已知需求

專案需求明示：**MCP 必須支援 2.0 版本或以上**。

此需求保留為 release gate，但在實作前必須把「2.0」轉成可測試的精確定義。

## 2. 版本語意注意事項

Model Context Protocol 官方 specification 使用日期格式的 protocol version（例如 `YYYY-MM-DD`），而不是 `2.0` 這種 semantic version。MCP payload 則通常建立於 JSON-RPC 2.0。

因此「MCP 2.0+」可能代表：

1. AgentMemoryOS MCP server／adapter 的產品版本 `>=2.0.0`；
2. 本專案 MCP adapter API 的 semantic version `>=2.0.0`；
3. JSON-RPC `2.0`；
4. 其他內部稱為 MCP 的元件版本。

在 owner 確認前，不應把以上任一解釋假裝成既定事實。

## 3. 暫定相容性契約

MVP 同時要求：

- transport payload 符合 JSON-RPC 2.0（若所選官方 MCP spec 仍使用該格式）；
- 官方 MCP `protocolVersion` 以日期版本明確 pin；
- adapter 自身使用 semantic version；
- 若 AgentMemoryOS MCP server 有 `2.x` 產品線，contract tests 的最低版本設定為 `>=2.0.0`；
- 不使用無上限的 major-version dependency 範圍，除非 compatibility CI 已覆蓋下一 major。

## 4. Hermes 整合基線

Hermes 可作為：

- MCP client：連接 local stdio 或 remote HTTP server；
- MCP server：對其他 client 暴露 Hermes 能力。

Bastet-EngramFlow 的 MVP 預設使用 **Hermes 作為 client，EngramFlow／AgentMemoryOS 端提供受治理工具介面**；最終方向仍須由 source-first assessment 與 threat model 決定。

## 5. 必測能力

- server discovery / startup
- tool listing 與 schema validation
- tool include/block filtering
- timeout、cancel 與 structured error mapping
- authentication（OAuth/bearer/mTLS 依部署需求）
- ACL / project scope 傳遞
- capability change / tool refresh
- unsupported protocol version handling
- duplicate request / idempotency
- malformed response 與 partial failure
- sensitive data redaction

## 6. Compatibility matrix

[COMPATIBILITY_MATRIX.md](COMPATIBILITY_MATRIX.md) 是唯一的相容性矩陣來源。`main`/nightly 可作 early-warning lane，不應在未評估下自動成為 production release gate。

## 7. 驗收條件

MCP 支援完成必須同時符合：

1. 精確記錄 client/server、implementation version 與 official protocol version。
2. 至少一條 transport 通過真實 end-to-end call。
3. unsupported version 能 fail clearly，不靜默降級。
4. policy filtering 在工具呼叫前生效。
5. 所有 tool call 可追溯至 proposal 與 policy decision。
6. 成功結果經 verifier read-back；不能只依 MCP response 宣告完成。

## 8. 需 Owner 決策

- 「MCP 2.0+」指的是哪個 component/version axis？
- MVP 要支援 stdio、HTTP，或兩者？
- 首個 official MCP protocol date baseline？
- 是否需要 Hermes 作為 MCP server 的反向使用情境？
