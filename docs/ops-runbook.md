# 齐谐科技 — 生产运维手册

## 环境信息

| 项目 | 值 |
|------|-----|
| 服务器 | 192.168.1.223 (OpenClaw Gateway) |
| 域名 | felix2026.cc.cd |
| 管理面板 | openclaw.qixie.tech → Portainer :9000 |
| Docker 版本 | 29.5.1 |
| Compose 版本 | v5.1.3 (plugin) |
| 操作系统 | Linux (Ubuntu/Debian) |

## 快速启动

### 首次部署

```bash
# 1. 克隆仓库
cd /home/felix
git clone https://github.com/felix2026/qixie-website.git qixie
cd qixie

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env, 填入实际值

# 3. 申请 SSL 证书
bash infra/ssl/setup.sh

# 4. 启动全栈服务
docker compose up -d
```

### 日常运维

```bash
# 查看服务状态
docker compose ps

# 查看日志
docker compose logs -f --tail=100
docker compose logs -f qixie-site

# 重启服务
docker compose restart qixie-site

# 更新部署 (拉取最新代码并重建)
git pull origin main
docker compose build
docker compose up -d
docker image prune -f
```

## SSL 证书管理

### 自动续期
certbot 容器每 12 小时自动检查续期。验证续期状态：

```bash
docker compose logs certbot
```

### 手动续期

```bash
docker compose run --rm certbot renew
docker compose restart nginx-proxy
```

### 证书路径
```
infra/ssl/certbot/conf/live/felix2026.cc.cd/
├── fullchain.pem    # 完整证书链
├── privkey.pem      # 私钥
└── chain.pem        # 中间证书
```

## 监控

### Portainer (Docker 管理)
- URL: http://192.168.1.223:9000 (内网)
- 域名: openclaw.qixie.tech (外网，SSL)
- 功能: 容器管理、日志查看、资源监控

### 高级监控 (可选, `--profile monitoring`)

```bash
# 启动监控栈
docker compose --profile monitoring up -d

# 访问
# cAdvisor: http://192.168.1.223:8081
# Node Exporter: http://192.168.1.223:9100/metrics
```

## 健康检查

```bash
# Nginx 代理层
curl -s http://felix2026.cc.cd/health
# 预期: "OK\n"

# 静态站点
curl -sI https://felix2026.cc.cd | head -5
# 预期: 200 OK, 安全头

# 所有容器健康状态
docker ps --filter "health=healthy"
```

## 备份

### 数据库 (待 CMP-129 PostgreSQL 启用后)

```bash
docker compose exec db pg_dump -U qixie qixie > backup_$(date +%Y%m%d).sql
```

### 证书备份

```bash
tar czf ssl-backup-$(date +%Y%m%d).tar.gz infra/ssl/certbot/conf/
```

## 故障排查

### 容器无法启动

```bash
docker compose logs --tail=50
docker compose ps -a
docker inspect <container_name>
```

### Nginx 502 Bad Gateway

```bash
# 检查上游服务是否运行
docker compose ps

# 检查 Nginx 配置语法
docker compose exec nginx-proxy nginx -t

# 检查日志
docker compose logs nginx-proxy --tail=50
```

### SSL 证书问题

```bash
# 检查证书是否过期
docker compose run --rm certbot certificates

# 强制续期
docker compose run --rm certbot renew --force-renewal
docker compose restart nginx-proxy
```

### 磁盘空间

```bash
# Docker 清理
docker system df
docker image prune -f
docker system prune -f  # 谨慎使用, 会删除所有停止的容器

# 日志清理 (journald)
sudo journalctl --vacuum-size=200M
```

## 安全建议

1. **防火墙**: 只开放 80/443 端口; 其他服务端口绑定 127.0.0.1
2. **SSH**: 禁用密码登录, 仅使用密钥
3. **自动更新**: 配置 unattended-upgrades 安全补丁
4. **日志审计**: 定期检查 Docker 和 Nginx 日志
5. **证书**: certbot 自动续期 + 每月手动检查
