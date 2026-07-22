# Aclclouds-Renew 自动续期脚本

基于 GitHub Actions 定时运行，使用 SeleniumBase 模拟浏览器登录 Discord OAuth，自动完成 [Aclclouds](https://dash.aclclouds.com) 项目的续期操作，并通过 Telegram 推送结果通知。为规避地域/风控限制，运行前会通过 sing-box 拉起本地代理隧道。

## 目录结构

```
.
├── .github/workflows/aclclouds.yml   # GitHub Actions workflow
├── aclclouds.py                       # 主任务脚本（登录 + 续期 + 通知）
└── generate_singbox_config.py         # 将代理节点链接转换为 sing-box 配置
```

## 工作流程

1. **Checkout & 安装依赖**：安装 `seleniumbase`、`requests`，并安装 Chromedriver。
2. **搭建代理隧道**：
   - 下载 `sing-box` 可执行文件；
   - 运行 `generate_singbox_config.py`，将 `PROXY` secret 解析为 `config.json`；
   - 校验配置后，在本地 `127.0.0.1:8080` 启动 socks5 混合入站，供后续脚本使用。
3. **执行续期任务（`xvfb-run` 无头虚拟显示 + CF 绕过模式）**：
   - 打开 Discord 登录页，用账号密码登录；
   - 跳转 Aclclouds 登录页，通过 Discord OAuth 授权；
   - 进入项目页面，判断是否存在 `Renew` 按钮；
   - 若存在则点击续期，处理"I am not a robot"验证及后续图片验证码；
   - 获取续期前后剩余时间，通过 Telegram 推送结果（含截图）。

## 环境变量 / Secrets 配置

请在仓库 **Settings → Secrets and variables → Actions** 中添加以下变量：

| 变量名 | 必填 | 说明 |
|---|:---:|---|
| `EMAIL` | ✅ | Discord 登录邮箱 |
| `PASSWORD` | ✅ | Discord 登录密码 |
| `PROXY` | ✅ | 代理节点链接（详见下方支持格式），用于生成本地 sing-box 隧道；留空会导致该步骤 `exit(1)`，整个 job 失败 |
| `TG_TOKEN` | ⭕ | Telegram Bot Token，用于推送通知 |
| `TG_CHAT_ID` | ⭕ | Telegram 接收消息的 chat_id |

> `TG_TOKEN` / `TG_CHAT_ID` 未配置时会自动跳过通知步骤，不影响主流程运行。

### 变量传递关系说明

`PROXY` 这个 secret 在 workflow 中被使用了两次，含义不同，容易混淆：

```
secrets.PROXY
   │
   ├─▶ 步骤"Setup Proxy Tunnel"中作为 PROXY_STR 传入
   │      generate_singbox_config.py 解析并生成 config.json
   │      （sing-box 监听 127.0.0.1:8080）
   │
   └─▶ 步骤"Run Task"中，PROXY 被固定写死为
          socks5://127.0.0.1:8080
          （指向上面本地启动好的 sing-box 出口）
          由 aclclouds.py 中 os.getenv("PROXY") 读取使用
```

### `PROXY` 支持的节点链接格式

`generate_singbox_config.py` 可以解析以下几类输入：

- 完整的 sing-box JSON 配置（原样透传）
- 单节点分享链接，支持协议：
  - `tuic://uuid:password@host:port?congestion_control=...&sni=...`
  - `hysteria2://` 或 `hy2://password@host:port?sni=...`
  - `vless://uuid@host:port?flow=...&security=tls|reality&sni=...&pbk=...&type=ws|grpc`
  - `trojan://password@host:port?sni=...`
  - `ss://base64(method:password)@host:port`
  - `vmess://base64(json配置)`
  - `socks5://user:pass@host:port`

## 触发方式

- **定时任务**：每 12 小时自动运行一次（`cron: '0 */12 * * *'`）
- **手动触发**：在 Actions 页面点击 `Run workflow`（`workflow_dispatch`）

## 常见问题

**Q: 为什么必须配置代理？**
A: Aclclouds / Discord 登录流程可能存在人机验证或地域限制，通过本地 sing-box 隧道转发流量可提高成功率。若目标环境无需代理，需要同时修改 workflow（移除代理搭建步骤）和 `aclclouds.py` 中 `proxy=PROXY_URL if PROXY_URL else None` 的逻辑，否则空 `PROXY` 会导致 sing-box 配置生成步骤直接失败。

**Q: 没有 Telegram 通知会报错吗？**
A: 不会。`aclclouds.py` 中对 `TG_TOKEN` / `TG_CHAT_ID` 做了判空处理，未配置时仅打印警告并跳过推送。

**Q: 出现验证码/人机验证怎么办？**
A: 脚本内置了针对"I am not a robot"按钮及后续图片验证码的自动化点击逻辑（最多重试 20 次），并在关键节点保存截图、推送到 Telegram 便于排查。

## 免责声明

本项目仅用于学习与个人自动化用途，请遵守目标网站的服务条款，因使用本脚本产生的任何后果由使用者自行承担。
