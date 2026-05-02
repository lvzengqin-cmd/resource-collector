# 每日资源采集系统

一个基于 Netlify + Supabase + GitHub Actions 的自动化资源采集管理系统。

## 功能特性

- 📊 **仪表盘**：实时查看采集统计数据
- 🔗 **多网盘支持**：夸克、百度、UC、迅雷
- ⚙️ **配置管理**：网盘 Cookies、采集源、定时任务
- 📋 **任务日志**：完整的任务执行记录
- ➕ **手动提交**：快速添加网盘链接
- ⏰ **自动采集**：每天定时执行，无需人工干预

## 技术架构

```
┌─────────────────────────────────────────────────┐
│           前端 (Netlify 静态托管)                 │
│   └── 纯 HTML/CSS/JS，直接连接 Supabase          │
├─────────────────────────────────────────────────┤
│           数据库 (Supabase PostgreSQL)           │
│   ├── resources - 资源数据                      │
│   ├── pan_config - 网盘配置                     │
│   ├── collect_sources - 采集源                 │
│   └── task_logs - 任务日志                     │
├─────────────────────────────────────────────────┤
│        自动化 (GitHub Actions)                   │
│   └── 每天定时触发采集脚本                       │
└─────────────────────────────────────────────────┘
```

## 快速部署

### 1. 上传到 GitHub

```bash
cd /workspace/resource-system
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/你的用户名/resource-collector.git
git push -u origin main
```

### 2. 配置 GitHub Secrets

在 GitHub 仓库的 Settings → Secrets 中添加：

| Secret 名称 | 值 |
|------------|-----|
| SUPABASE_URL | 你的 Supabase 项目 URL |
| SUPABASE_ANON_KEY | 你的 Supabase Anon Key |

### 3. 部署到 Netlify

1. 访问 [Netlify](https://app.netlify.com)
2. 点击 "Add new site" → "Import an existing project"
3. 选择 GitHub 并授权
4. 选择 `resource-system` 仓库
5. 设置：
   - Build command: `echo "No build needed"`
   - Publish directory: `dist`
6. 点击 "Deploy site"

### 4. 配置定时任务

GitHub Actions 已配置为每天 UTC 1:00（北京时间 9:00）自动执行采集任务。

也可以手动触发：在 GitHub 仓库的 Actions 页面，点击 "Run workflow"

## 数据库表结构

### resources（资源表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | serial | 主键 |
| title | text | 资源标题 |
| description | text | 资源描述 |
| pan_type | text | 网盘类型 |
| original_link | text | 原始链接 |
| extract_code | text | 提取码 |
| status | text | 状态 |
| views | int | 浏览次数 |
| created_at | timestamp | 创建时间 |

### pan_config（网盘配置表）

| 字段 | 类型 | 说明 |
|------|------|------|
| pan_type | text | 网盘类型（主键） |
| cookies | text | Cookies |
| target_dir | text | 转存目录 |
| enabled | bool | 是否启用 |

### collect_sources（采集源表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | serial | 主键 |
| name | text | 名称 |
| url | text | URL |
| enabled | bool | 是否启用 |
| created_at | timestamp | 创建时间 |

### task_logs（任务日志表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | serial | 主键 |
| task_type | text | 任务类型 |
| status | text | 状态 |
| summary | jsonb | 汇总数据 |
| error | text | 错误信息 |
| start_time | timestamp | 开始时间 |
| end_time | timestamp | 结束时间 |
| duration | int | 耗时（秒） |

## 使用说明

### 手动提交资源

1. 打开管理界面
2. 进入「手动提交」页面
3. 输入资源标题和描述
4. 粘贴网盘链接（支持多个，每行一个）
5. 点击「提交资源」

### 配置网盘

1. 进入「网盘配置」页面
2. 选择要配置的网盘类型
3. 粘贴 Cookies
4. 设置转存目录
5. 点击保存

### 查看采集日志

1. 进入「任务日志」页面
2. 筛选任务类型或状态
3. 点击查看详情

## 自动化流程

```
┌──────────────────────────────────────────────────────────┐
│                     每日自动采集流程                       │
├──────────────────────────────────────────────────────────┤
│  1. GitHub Actions 定时触发 (每天 9:00 北京时间)          │
│  ↓                                                        │
│  2. 执行 collector.py 采集脚本                            │
│  ↓                                                        │
│  3. 从配置的采集源网页提取网盘链接                         │
│  ↓                                                        │
│  4. 去重后存入 Supabase 数据库                            │
│  ↓                                                        │
│  5. 生成任务日志                                          │
│  ↓                                                        │
│  6. 管理界面实时显示最新数据                               │
└──────────────────────────────────────────────────────────┘
```

## 本地开发

```bash
# 克隆仓库
git clone https://github.com/你的用户名/resource-collector.git
cd resource-collector

# 安装依赖
pip install supabase requests beautifulsoup4 lxml

# 运行采集脚本
python collector.py

# 本地预览前端
cd dist && python -m http.server 8080
```

## 注意事项

1. **Cookies 安全**：网盘 Cookies 包含敏感信息，请妥善保管
2. **频率限制**：自动采集设置合理间隔，避免被目标网站封禁
3. **数据备份**：定期备份 Supabase 数据库
4. **GitHub Actions**：免费额度足够个人使用（每月2000分钟）

## License

MIT License
