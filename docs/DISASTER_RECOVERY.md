# StockAI 灾难恢复手册

## 备份体系

| 备份内容 | 位置 | 频率 | 保留 |
|----------|------|------|------|
| 数据库 (app.db) | GitHub backups 分支 + Railway 卷 | 每日 03:00 | 30天 |
| 环境变量快照 | GitHub backups 分支 | 每日 | 30天 |
| 源代码 | GitHub main 分支 | 每次 push | 永久 |
| Railway 自动备份 | Railway 卷 /data/backups/ | 应用关闭时 | 10份 |
| ECS 代理配置 | 阿里云 ECS /root/ | 手动 | - |

## 恢复流程

### 场景 1：Railway 服务崩溃

```
1. railway status                    # 确认状态
2. railway logs --lines 50           # 查看崩溃原因
3. railway redeploy                  # 重新部署
4. 如果不行：railway up --yes        # 强制重新部署
```

### 场景 2：Railway 卷损坏/丢失

```
1. 新建 Railway 卷并挂载
2. 从 GitHub backups 分支恢复 app.db
3. railway up --yes                  # 部署
4. 验证：curl /health
```

### 场景 3：ECS 代理宕机

```
1. SSH root@47.97.66.164 (密码: Xorpay2026)
2. iptables -I INPUT -p tcp --dport 8444 -j ACCEPT
3. cd /root && nohup python3 ep2.py 8444 > /tmp/ep2.log 2>&1 &
4. 或通过阿里云 API 重启实例
```

### 场景 4：GitHub 仓库被删

```
从本地 git 仓库 push 回去：
git remote add origin git@github.com:h358316896-ai/stock-analysis-app.git
git push -u origin main --force
```

### 场景 5：全站瘫痪

优先级：
1. 恢复 GitHub 仓库
2. Railway 重新部署
3. 恢复数据库从 GitHub backups 分支
4. 恢复 ECS 代理
5. 验证核心 API：/health、/api/market/gold、/api/stock/search
6. 验证 kunhuang.top 首页正常加载

## 环境变量清单

### Railway 变量（关键项）
```
FLASK_SECRET_KEY=e952...
XORPAY_SECRET=d7c2...
XORPAY_AID=705874
PUBLIC_URL=https://kunhuang.top
EASTMONEY_PROXY=http://47.97.66.164:8444/
DEEPSEEK_API_KEY=sk-...
WXPUSHER_APP_TOKEN=AT_mn...
```

### ECS 代理配置
```
实例 ID: i-bp1hpe4gi95nig68ksgq
IP: 47.97.66.164
代理代码: /root/ep2.py (端口 8444)
XORPay 代理: /root/px2.py (端口 8443/9876)
备份在 GitHub: _new_proxy.py 参考实现
```

## 监控指标

- Railway 健康: `curl /health` → status=ok
- 数据源状态: `curl /api/health/data-sources` → green/yellow/red
- ECS 代理: `curl http://47.97.66.164:8444/`
- GitHub Actions: 检查 backup workflow 运行状态

## 紧急联系

- Railway 控制台: https://railway.com/project/f7b11aa6
- 阿里云 ECS 控制台: https://ecs.console.aliyun.com
- GitHub: https://github.com/h358316896-ai/stock-analysis-app
- WxPusher: https://wxpusher.zjiecode.com/admin
