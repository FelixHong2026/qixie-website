# 齐谐科技官网 - Qixie Technology Website

齐谐科技官方网站，部署于 GitHub Pages。

## 部署步骤

### 1. 创建 GitHub 仓库
1. 访问 https://github.com/new
2. 仓库名：`qixie-website`（或任意名称）
3. 设为 Public（GitHub Pages 需要）
4. 创建后，在本地执行：
   ```bash
   git remote set-url origin https://github.com/<你的用户名>/qixie-website.git
   git push -u origin main
   ```

### 2. 启用 GitHub Pages
1. 进入仓库 → Settings → Pages
2. Source: 选择 `main` 分支，`/(root)` 目录
3. 点击 Save
4. 等待几分钟，网站将在 `https://<用户名>.github.io/qixie-website/` 可用

### 3. 配置自定义域名
1. 在 GitHub Pages 设置中，Custom domain 输入 `felix2026.cc.cd`
2. 点击 Save
3. GitHub 会自动在仓库中添加 CNAME 文件（已预置）

### 4. DNS 配置（Cloudflare）
域名 felix2026.cc.cd 已托管在 Cloudflare DNS。

需要在 Cloudflare 控制面板中设置 DNS 记录：

| 类型 | 名称 | 值 | 代理状态 |
|------|------|-----|---------|
| A | @ | 185.199.108.153 | DNS only（灰云）→ 验证后改 Proxied |
| A | @ | 185.199.109.153 | DNS only（灰云）→ 验证后改 Proxied |
| A | @ | 185.199.110.153 | DNS only（灰云）→ 验证后改 Proxied |
| A | @ | 185.199.111.153 | DNS only（灰云）→ 验证后改 Proxied |

**注意**：配置前先删除现有的 A 记录（104.21.46.53 和 172.67.223.225）。

### 5. 验证
- 访问 `https://felix2026.cc.cd` 确认网站正常
- 在 GitHub Pages 设置中确认 HTTPS 已启用

## 本地开发
```bash
# 启动本地预览
python3 -m http.server 8000
# 访问 http://localhost:8000
```
