# Antigravity: cài v0.11.0 và giữ riêng từng hội thoại

Bản này dùng native PreToolUse hook của Antigravity2.22.0 và MCP riêng để giữ
conversation ID. Mỗi chat có flow riêng; đổi model không tạo flow mới. Codex dùng
facade hiện tại. Ba nhãn gửi Helen mặc định là `Antigravity`, `Gemini model`, `a2a`;
nhãn model được đổi bằng tham số `model`, không tự xác minh backend model.

## 1. Client daemon phải hoạt động

Client và server cài cùng wheel v0.11.0. Máy mới cần Python3.11, daemon, HTTPS/device
token/CA riêng theo [hướng dẫn client](client-codex.vi.md) và [SSH nếu dùng](ssh-tunnel.vi.md).
Antigravity chỉ dùng explicit get/wait; các yêu cầu Codex/native queue trong hướng
dẫn đó chỉ áp dụng khi dùng Codex. Không sao chép inbox/keys của thiết bị khác;
thiết bị mới cần token được cấp riêng. Không dán credentials vào chat hoặc MCP config.

Nếu máy đã có client: giữ nguyên cấu hình, device ID, token, payload key và dữ liệu.
Dừng đúng service daemon đang dùng, chờ writer.lock được nhả, sao lưu nhất quán
SQLite (SQLite backup API) cùng cấu hình/khóa ở nơi riêng, rồi thay code bằng wheel
đã xác minh và khởi động lại đúng một daemon. Giữ wheel/venv cũ để rollback code;
không phục hồi DB cũ đè lên công việc mới. Xem [upgrade/rollback](../upgrades/upgrade-v0.9.md)
cho các nguyên tắc và receiver overlay; nâng0.9→0.10 không thay receiver/schema.
Không chạy khối cài mới nếu venv hoặc inbox đã tồn tại.

Tải đủ assets để kiểm tra toàn bộ SHA256SUMS (khối này chỉ tải, chưa thay code):

```bash
(
set -eu
release_dir="$HOME/.local/share/hermes-a2a-gateway/releases/0.11.0"
mkdir -p "$release_dir"
release_url=https://github.com/phamviet86/hermes-a2a-gateway/releases/download/v0.11.0
for asset in hermes_a2a_gateway-0.11.0-py3-none-any.whl hermes_a2a_gateway-0.11.0.tar.gz hermes-a2a-compat.patch hermes-a2a-compat.json hermes-a2a-sender-722bced.patch hermes-a2a-sender-722bced.json hermes_patch.py SHA256SUMS; do
  curl --fail --location --output "$release_dir/$asset" "$release_url/$asset"
done
if command -v shasum >/dev/null 2>&1; then
  (cd "$release_dir" && shasum -a 256 -c SHA256SUMS)
else
  (cd "$release_dir" && sha256sum --check SHA256SUMS)
fi
)
```

Sau khi dừng daemon và sao lưu, cài wheel vào venv hiện tại (không cài vào venv
của Hermes), rồi chạy pip check và khởi động daemon theo service đang dùng:

```bash
"$HOME/.local/share/hermes-a2a-gateway/venv/bin/python" -m pip install \
  "$HOME/.local/share/hermes-a2a-gateway/releases/0.11.0/hermes_a2a_gateway-0.11.0-py3-none-any.whl"
"$HOME/.local/share/hermes-a2a-gateway/venv/bin/python" -m pip check
"$HOME/.config/hermes-a2a-gateway/launch" client-doctor
```

Nếu doctor báo socket/service chưa chạy, hoàn tất khởi động service trước khi
đăng ký MCP. Không thay token, state path hoặc tạo daemon thứ hai để vượt lỗi.

## 2. Hợp nhất cấu hình Antigravity

Dừng các lượt gateway đang chạy và giữ operation_id. Khối dưới sao lưu nguyên
cấu hình hiện tại vào thư mục riêng, thay đúng entry gateway và thêm đúng hook;
không thay các server/hook khác. Chỉ chạy khi chưa có hook cùng tên hoặc hook hiện
tại đúng là adapter này. Python path tuyệt đối được tạo từ HOME của máy đang cài.

```bash
"$HOME/.local/share/hermes-a2a-gateway/venv/bin/python" - <<'PY'
import json, os, shlex, shutil, tempfile
from pathlib import Path
from importlib.metadata import version
os.umask(0o077)
assert version('hermes-a2a-gateway') == '0.11.0'
home = Path.home()
python = home / '.local/share/hermes-a2a-gateway/venv/bin/python'
base = home / '.gemini/config'
base.mkdir(parents=True, exist_ok=True)
mcp_file, hook_file = base/'mcp_config.json', base/'hooks.json'
for p in (mcp_file, hook_file):
    if p.is_symlink():
        raise SystemExit('Config symlink: inspect the selected config path before changing it.')
mcp = json.loads(mcp_file.read_text()) if mcp_file.exists() else {}
hooks = json.loads(hook_file.read_text()) if hook_file.exists() else {}
assert isinstance(mcp, dict) and isinstance(hooks, dict)
if 'hermes-a2a-binding' in hooks:
    raise SystemExit('Hook already exists; inspect/reuse it instead of replacing it blindly.')
servers = mcp.setdefault('mcpServers', {})
assert isinstance(servers, dict)
prior = servers.get('hermes-a2a-gateway', {})
assert isinstance(prior, dict)
env = dict(prior.get('env', {}))
env.update(HERMES_A2A_GATEWAY_CLIENT_HARNESS='antigravity',
           HERMES_A2A_GATEWAY_CLIENT_HARNESS_INSTANCE='antigravity-desktop')
# Same protected default registry for hook and facade. Preserve any selected socket settings.
registry = str(home / '.local/state/hermes-a2a-gateway/antigravity')
env['HERMES_A2A_GATEWAY_ANTIGRAVITY_BINDING_DIR'] = registry
servers['hermes-a2a-gateway'] = {**prior, 'command': str(python),
    'args': ['-m', 'hermes_a2a_gateway.antigravity_mcp'], 'env': env}
hooks['hermes-a2a-binding'] = {'PreToolUse': [{'matcher': 'call_mcp_tool', 'hooks': [{
    'type': 'command', 'command': 'HERMES_A2A_GATEWAY_ANTIGRAVITY_BINDING_DIR=' +
        shlex.quote(registry) + ' ' + shlex.quote(str(python)) +
        ' -m hermes_a2a_gateway.antigravity_binding', 'timeout': 10}]}]}
backup_root = home / '.local/share/hermes-a2a-gateway/config-backups'
backup_root.mkdir(parents=True, exist_ok=True)
backup = Path(tempfile.mkdtemp(prefix='antigravity-0.10-', dir=backup_root))
for p in (mcp_file, hook_file):
    if p.exists():
        shutil.copy2(p, backup/p.name)
        (backup/p.name).chmod(0o600)
for p, value in ((mcp_file, mcp), (hook_file, hooks)):
    fd, tmp = tempfile.mkstemp(dir=base)
    with os.fdopen(fd, 'w') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')
    os.replace(tmp, p)
print('Configured gateway and native hook. Private rollback config:', backup)
PY
```

Nếu daemon dùng state/socket tùy chỉnh, facade cần cùng
`HERMES_A2A_GATEWAY_CLIENT_STATE_DIR`.
Hợp nhất giá trị đúng theo [technical guide](../reference/antigravity.md); không đoán hoặc tạo
identity bằng model. Quyền Ask của app vẫn áp dụng; hook không tự auto-allow tool.

## 3. Mở lại và thử

Đóng/mở lại Antigravity để nạp MCP mới. Kiểm tra năm tool gateway đều có
`request_key`. Mỗi hành động mới dùng UUID ngẫu nhiên mới, lưu key và nguyên
arguments. Retry submit dùng cùng key và nguyên arguments; timeout không cho phép
gửi công việc bằng key mới. Kết quả chưa rõ thì get/wait trên operation_id đã lưu.

Trong hai chat mới A/B, yêu cầu gửi hai marker tổng hợp khác nhau tới Helen, chỉ
trả JSON ba nhãn và marker. B phải không biết marker A; hai operation/flow khác nhau.
Đổi model thật ở bộ chọn trong A, submit công việc mới kèm nhãn `model` phù hợp,
yêu cầu nhớ marker cũ mà không nhắc lại marker trong prompt. Mở lại đúng chat B cũ
và làm kiểm tra nhớ marker tương tự. Gửi lại operation_id và phản hồi Helen để đối
chiếu. Không cho agent chạy shell/đọc DB để vượt lỗi identity.

Rollback cấu hình chỉ phục hồi entry gateway trước đó và gỡ hook vừa thêm;
giữ các entry khác và registry/attestation.key hiện tại. Không ghi đè toàn bộ file
backup nếu đã có thay đổi mới. Generic facade0.9 không hỗ trợ native Antigravity.
Giữ registry và khóa cùng nhau; quyền sở hữu retry key không tự hết hạn.

Kiểm chứng thực tế: hai chat đồng thời, retry, chặn truy cập chéo và đổi model đã
đạt trên candidate/Antigravity2.22.0. Kiểm tra mở lại sau khi đã có context chờ người
dùng thực hiện. Không có native push cho Antigravity và chưa hỗ trợ Windows.
