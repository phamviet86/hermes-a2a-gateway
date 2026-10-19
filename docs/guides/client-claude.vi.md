# Claude Code Desktop: cài đặt và kiểm tra v0.11.0

English: [Quickstart](quickstart.md).

Named brokers: [Client connections](client-connections.md).

Phạm vi đầu tiên là **Code tab của Claude Desktop**, không phải chat thường.
CLI/IDE, resume thực tế, khởi động lại process và liên thông CLI/Desktop **chưa
được xác minh**. Đăng nhập Desktop không đồng nghĩa CLI đã đăng nhập; không trích
credential Desktop để cấp cho CLI. Xem [hợp đồng](../reference/claude-code.md).

## Cấu hình

**Máy đã có client v0.11.0 hoạt động:** dùng lại daemon, venv, inbox, key và
transport hiện có; chỉ đăng ký MCP + hook cho project thực tế. Không cài lại wheel,
không sao chép credential và không chạy daemon thứ hai. Cấu hình project tạm của
ca nghiệm thu đã được gỡ; nghiệm thu thành công không tự cấu hình project của bạn.

**Máy mới:** cài wheel phát hành đã kiểm checksum với Python 3.11 theo
[deployment](deployment.md), rồi thiết lập transport, device token/CA và một
client daemon theo [hướng dẫn client](client-codex.vi.md). Các bước đăng ký MCP
Codex/native queue trong hướng dẫn đó không áp dụng cho Claude; dùng MCP + hook
bên dưới. Máy đã có phiên bản cũ làm [upgrade v0.11](../upgrades/upgrade-v0.11.md)
với backup/rollback, không chạy khối tạo inbox mới.

Venv mặc định là `~/.local/share/hermes-a2a-gateway/venv`. Xác định đường dẫn tuyệt
đối trên máy; JSON không tự mở rộng `~` hoặc `$HOME`. Ví dụ trên máy đã nghiệm thu,
`/absolute/gateway-venv` bên dưới là
`/Users/phamviet86/.local/share/hermes-a2a-gateway/venv`.
Kiểm tra phiên bản bằng `venv/bin/hermes-a2a-gateway --version` và trạng thái bằng
launcher được cài `~/.config/hermes-a2a-gateway/launch client-doctor`; nếu launcher
không có, dùng quy trình doctor của service hiện tại, không dựng daemon mới.

Dùng instance ổn định `claude-desktop`. Đổi instance tạo namespace mới và mất quyền
đọc operation cũ từ namespace mới; không đổi tên để giả lập resume hoặc dùng chung
với CLI chưa kiểm chứng. Sender label mặc định Claude / Claude model / a2a chỉ là
nhãn mô tả.

Trong project Desktop đã được người dùng tin cậy, **merge** entry sau vào
`.mcp.json`; không thay thế các server hoặc cấu hình khác:

```json
{
  "mcpServers": {
    "hermes-a2a-gateway": {
      "command": "/absolute/gateway-venv/bin/hermes-a2a-gateway",
      "args": ["client-mcp"],
      "env": {
        "HERMES_A2A_GATEWAY_CLIENT_HARNESS": "claude",
        "HERMES_A2A_GATEWAY_CLIENT_HARNESS_INSTANCE": "claude-desktop",
        "HERMES_A2A_GATEWAY_CLIENT_IDENTITY": "hook:claude"
      }
    }
  }
}
```

Merge hook vào `.claude/settings.local.json` của project; giữ nguyên hooks và
permission policy khác. Cấu hình project này đã được kiểm chứng trong Desktop. Đây cũng là cấu hình
thường trực cho project nếu bạn giữ hai file tại đó; không cần đặt trong thư mục
test. Kiểm tra entry/hook cùng tên trước khi merge để tránh đăng ký hai lần.
User-scope là lựa chọn riêng khi cần nhiều project, nhưng chưa được nghiệm thu
trong dự án này: chỉ chọn khi operator yêu cầu và xác minh cách Desktop nạp cả MCP
lẫn hook; không suy ra từ đăng ký CLI hoặc sao chép tùy tiện vào config toàn cục.

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "mcp__hermes-a2a-gateway__.*",
      "hooks": [{
        "type": "command",
        "command": "/absolute/gateway-venv/bin/python -m hermes_a2a_gateway.host_hook --profile claude",
        "timeout": 10
      }]
    }]
  }
}
```

Nếu đường dẫn có dấu cách, quote executable trong chuỗi lệnh hook. Không chèn
prompt, token hoặc tham số model vào lệnh. MCP và hook dùng chung registry mặc định
`~/.local/state/hermes-a2a-gateway/claude`. Nếu cần override, cấp cùng
`HERMES_A2A_GATEWAY_CLAUDE_BINDING_DIR` qua cấu hình launcher do operator sở hữu cho
cả hai process; không dùng registry Antigravity. `HERMES_A2A_GATEWAY_MCP_SERVER_NAME`
đổi tên server mà hook kiểm tra; nếu đổi thì phải đồng bộ entry MCP và matcher.
Thêm `HERMES_A2A_GATEWAY_CLIENT_STATE_DIR` cho MCP nếu daemon dùng inbox khác mặc định.

Wrapper Codex `launch` hiện lọc các biến gateway từ môi trường cha. Vì thế dùng
executable venv trực tiếp như trên; không giả định wrapper đó giữ biến harness.
MCP không cần token broker: daemon hiện có sở hữu transport và authentication.

## Kiểm tra có giới hạn

Mở một Code session mới trong project và giữ normal permission flow (probe dùng
Manual và Allow once). Xác nhận 5 tool có schema như Codex, không có request_key
hay conversation ID do model khai báo. Hook không tự approve thao tác.

Gửi một prompt vô hại được operator cho phép, lưu operation_id, rồi get/wait đúng
operation. Không resubmit khi chưa rõ kết quả. Đọc chéo operation từ session khác
phải bị từ chối; báo cáo rõ code/result thực tế. Subagent dùng cùng flow với cha,
phải truyền operation_id về cha và viết prompt đủ ngữ cảnh. Chỉ lấy kết quả chủ
động; không có push/wake cho Claude.

Attestation hết hạn sau 300 giây và dùng một lần. Duyệt quá chậm phải tạo lời gọi
host mới; điều đó không cho phép gửi lại một submit đã có kết quả chưa rõ.
Compaction và mở lại sidebar đã giữ ID trong probe; fork và clear đổi ID. Không
suy rộng thành bằng chứng resume hoặc restart. Probe chỉ chứng minh host identity;
live gateway acceptance, CI và cài release được báo cáo riêng.

## Rollback

Trước sửa cấu hình, lưu bản rollback riêng có quyền hạn chế. Chỉ dừng các test
turn của mình trước khi refresh host. Khôi phục entry MCP đã lưu và gỡ đúng hook
entry mình thêm, không xóa server/hook khác. Giữ nguyên registry/key, inbox, IDs,
operation, account và credentials. Không ghi đè database hiện tại bằng backup cũ.
Nếu gỡ hook mà MCP cũ còn được load, binding đã cấp có thể còn hiệu lực đến TTL;
không coi xóa cấu hình là thu hồi tức thì. Việc refresh/restart Desktop và hành vi
resume cần được kiểm tra riêng trong ca có phép, không suy ra từ cài wheel thành công.

## Năm tool và cách dùng

| Tool | Mục đích |
| --- | --- |
| `gateway_submit` | Gửi một công việc mới đã được cho phép; `wait_seconds` 0–60, bỏ trống dùng mặc định daemon |
| `gateway_get` | Đọc operation đã lưu trong đúng session sở hữu |
| `gateway_wait` | Chờ operation đó, `timeout` 0–60, mặc định 30 giây |
| `gateway_cancel` | Yêu cầu hủy best-effort; không chứng minh upstream đã dừng |
| `gateway_upload_artifact` | Upload file local chỉ khi người dùng yêu cầu rõ; không tự gửi file |

Claude không có `request_key`. Lưu operation/result ID, đọc nội dung kết quả trước
khi kết luận. Timeout/ACK không rõ: get/wait operation đã lưu, không submit lại;
không có ID thì báo cần đối chiếu, không tạo session/instance khác để vượt lỗi.
Rate limit: đọc `retry_at`, không tự lặp submit. Xem thêm
[quy tắc vận hành](ai-operations.md).

## Prompt có thể giao cho Claude Code Desktop

Dán trong **Code tab của project cần cấu hình**; đây là yêu cầu cấu hình khi
operator chủ động gửi, không phải yêu cầu cài mới daemon:

> Đọc docs/guides/client-claude.vi.md trong repo hermes-a2a-gateway. Cấu hình
> project hiện tại dùng client v0.11.0 đã cài. Xác minh venv độc lập và doctor;
> backup riêng rồi merge đúng một MCP hermes-a2a-gateway vào .mcp.json và một
> PreToolUse hook vào .claude/settings.local.json. Dùng trực tiếp executable
> trong ~/.local/share/hermes-a2a-gateway/venv với đường dẫn tuyệt đối, harness
> claude, instance claude-desktop, identity hook:claude; hook là python -m
> hermes_a2a_gateway.host_hook --profile claude. Giữ settings, auth, permissions,
> registry và daemon hiện có, không đọc/in token. Không dùng wrapper Codex cho
> facade. Nếu cần reload, lưu operation đang có và yêu cầu mở Code session mới
> trong project; không force quit app. Báo lại file/entry đã merge và năm tool.
> Không tự gửi công việc tới Helen trong bước cấu hình.

Prompt sử dụng sau khi host đã nạp MCP/hook:

> Dùng hermes-a2a-gateway gửi đúng một yêu cầu vô hại: “Chỉ trả lời ACK-SETUP;
> không dùng tool, sửa file hay lưu memory.” Chọn wait_seconds=30, lưu operation_id,
> rồi gateway_get cùng ID trong chat này; nếu còn pending thì gateway_wait tối đa
> 30 giây. Không resubmit khi kết quả chưa rõ. Báo operation_id, state và nội dung
> trả về thực tế. Không upload file hoặc thay quyền.

Bằng chứng cài release/native submit-get:
[nghiệm thu ba host v0.11.0](../reports/native-acceptance-v0.11.0-2026-10-14-attempt5.md).
Các giới hạn CLI/IDE/resume phía trên vẫn giữ nguyên.
