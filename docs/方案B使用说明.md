# 方案B：浏览器自动转存使用说明

> 版本: v1.0  
> 更新: 2026-05-04

---

## 一、功能概述

方案B实现网盘资源的**浏览器自动化转存**，将采集到的资源自动转存到你的网盘账户。

### 支持平台

| 平台 | 状态 | 说明 |
|------|------|------|
| 夸克网盘 | ✅ | Playwright 自动化 |
| 百度网盘 | ✅ | Playwright 自动化 |
| UC网盘 | 📋 | 待开发 |
| 迅雷网盘 | 📋 | 待开发 |

---

## 二、快速开始

### 2.1 安装依赖

```bash
pip install playwright
playwright install chromium
```

### 2.2 配置Cookie

在 `config.py` 中配置你的网盘Cookie：

```python
# 夸克Cookie
QUARKE_COOKIE = "你的夸克Cookie"

# 百度Cookie
BAIDU_COOKIE = "你的百度Cookie"
```

### 2.3 获取Cookie

#### 夸克网盘Cookie
1. 打开夸克网盘 https://pan.quark.cn
2. 登录你的账户
3. 按 F12 打开开发者工具
4. 切换到 Network（网络）标签
5. 刷新页面，查找任意请求
6. 在 Request Headers 中找到 `cookie` 字段
7. 复制完整的Cookie值

#### 百度网盘Cookie
1. 打开百度网盘 https://pan.baidu.com
2. 登录你的账户
3. 按 F12 打开开发者工具
4. 切换到 Application（应用）标签
5. 在左侧找到 Cookies -> https://pan.baidu.com
6. 复制 BDUSS 和 STOKEN 的值

### 2.4 启用自动转存

在 `config.py` 中修改：

```python
# 启用自动转存
ENABLE_AUTO_TRANSFER = True
```

### 2.5 运行测试

```bash
# 测试采集（不会触发转存）
python collector.py --test

# 完整运行（采集+转存）
python collector.py
```

---

## 三、手动转存

### 3.1 单个资源转存

```bash
python transfer.py --link "https://pan.quark.cn/s/xxxx" --title "测试资源"
```

### 3.2 指定网盘类型

```bash
python transfer.py --link "https://pan.baidu.com/s/xxxx" --type "百度" --code "1234"
```

### 3.3 批量转存

创建 `resources.json` 文件：

```json
{
  "resources": [
    {
      "title": "资源标题1",
      "pan_type": "夸克",
      "pan_link": "https://pan.quark.cn/s/xxxxx",
      "extract_code": ""
    },
    {
      "title": "资源标题2",
      "pan_type": "百度",
      "pan_link": "https://pan.baidu.com/s/xxxxx",
      "extract_code": "1234"
    }
  ]
}
```

运行批量转存：

```bash
python transfer.py --batch resources.json --delay 5
```

---

## 四、配置项说明

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `ENABLE_AUTO_TRANSFER` | `False` | 是否启用自动转存 |
| `TRANSFER_DIR` | `"资源采集"` | 转存目标文件夹 |
| `AUTO_SHARE` | `True` | 转存后自动分享 |
| `SHARE_EXPIRE` | `7` | 分享链接有效期(天) |
| `TRANSFER_DELAY` | `5` | 批量转存间隔(秒) |

---

## 五、注意事项

### 5.1 Cookie有效期

- 网盘Cookie通常有时效性
- 建议定期更新Cookie
- 失效后需要重新获取

### 5.2 反爬机制

- 夸克/百度有严格反爬
- 建议设置较长的间隔时间
- 避免短时间内大量转存

### 5.3 GitHub Actions限制

- Playwright需要安装浏览器（约200MB）
- GitHub Actions执行时间较长
- 建议仅在本地测试后手动启用

### 5.4 成功率

- 公开分享链接转存成功率较高
- 私密链接需要提取码
- 部分资源可能已被转存过

---

## 六、故障排除

### 6.1 浏览器初始化失败

```
❌ 浏览器初始化失败
```

解决方案：
```bash
# 重新安装 Chromium
playwright install chromium
```

### 6.2 Cookie设置失败

```
❌ Cookie设置失败
```

解决方案：
1. 检查Cookie格式是否正确
2. 确认Cookie是否过期
3. 重新获取新的Cookie

### 6.3 登录失败

```
⚠️ 未登录或登录已过期
```

解决方案：
1. 更新Cookie
2. 确认账户状态正常

---

## 七、工作原理

```
采集任务完成
     │
     ▼
检测到 ENABLE_AUTO_TRANSFER = True
     │
     ▼
从数据库获取最近入库资源
     │
     ▼
逐个资源执行转存
     │
     ├──► 访问分享链接
     ├──► 登录网盘
     ├──► 点击转存按钮
     ├──► 选择目标文件夹
     └──► 确认转存
     │
     ▼
发送通知（成功/失败）
```

---

## 八、扩展开发

### 8.1 添加新网盘平台

参考 `transfer.py` 中的基类实现：

```python
class NewPlatformTransfer(BaseTransfer):
    BASE_URL = "https://xxx.com"
    
    def __init__(self, cookie: str = None):
        super().__init__(cookie or CONFIG_COOKIE, "新平台")
    
    def set_cookie(self) -> bool:
        # 实现Cookie设置
        pass
    
    def check_login(self) -> bool:
        # 实现登录检查
        pass
    
    def transfer(self, resource: Resource) -> TransferResult:
        # 实现转存逻辑
        pass
```

### 8.2 添加失败重试

```python
def transfer_with_retry(resource: Resource, max_retries: int = 3):
    for attempt in range(max_retries):
        result = transfer_resource(resource)
        if result.success:
            return result
        time.sleep(10 * (attempt + 1))  # 递增等待
    return result
```

---

## 九、相关文件

| 文件 | 说明 |
|------|------|
| `transfer.py` | 转存模块主文件 |
| `config.py` | 配置文件 |
| `collector.py` | 采集主程序（已集成转存） |

---

## 十、更新日志

### v1.0 (2026-05-04)
- 初始版本
- 支持夸克网盘、百度网盘
- 支持单资源转存、批量转存
