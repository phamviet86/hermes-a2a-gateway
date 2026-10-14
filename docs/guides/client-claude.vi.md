# Claude Code Desktop: cài đặt và kiểm tra v0.11.0

Phạm vi đầu tiên là **Code tab của Claude Desktop**, không phải chat thường.
CLI/IDE, resume thực tế, khởi động lại process và liên thông CLI/Desktop **chưa
được xác minh**. Đăng nhập Desktop không đồng nghĩa CLI đã đăng nhập; không trích
credential Desktop để cấp cho CLI. Xem [hợp đồng](../reference/claude-code.md).

## Cấu hình

Cài wheel phát hành đã kiểm checksum theo [deployment](deployment.md), dùng Python
3.11 và giữ nguyên daemon/inbox/key đang có. Chưa có release thì không coi wheel
build từ checkout là artifact phát hành. Xác định đúng executable tuyệt đối của
venv độc lập; không cài vào môi trường Hermes. Không chạy daemon thứ hai lên inbox.

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
permission policy khác. Cấu hình project này đã được kiểm chứng trong probe
Desktop. Không quảng bá user-scope/CLI registration như một ca đã kiểm chứng.

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
