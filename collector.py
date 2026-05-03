#!/usr/bin/env python3
"""
每日资源采集系统 v2.2
支持夸克、百度、UC、迅雷、Kdocs网盘的自动化采集
修复内容：
1. Resource类与数据库表结构匹配
2. 修复URL编码问题
3. 添加全局去重机制
4. 修复pan_link为空检查
5. 添加日志记录功能
6. 添加统计信息持久化
7. 新增Kdocs采集器
"""

import os
import re
import json
import time
import random
import hashlib
from datetime import datetime
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import requests
import urllib.parse

from config import (
    SUPABASE_URL, SUPABASE_KEY,
    QUARKE_COOKIE, BAIDU_COOKIE, UC_COOKIE, XL_COOKIE,
    TRANSFER_DIR, AUTO_SHARE, SHARE_EXPIRE, EXTRACT_CODE,
    COLLECT_SOURCES
)

@dataclass
class Resource:
    """资源数据模型 - 与数据库表结构匹配"""
    title: str
    pan_type: str
    pan_link: str  # 网盘链接（原始链接保存到这里）
    original_link: str = ""  # 兼容字段，内部使用
    extract_code: Optional[str] = None
    description: Optional[str] = None
    category: str = "其他"
    status: str = "pending"
    views: int = 0
    share_link: Optional[str] = None  # 内部使用，不保存到DB
    # 内部使用
    _link_hash: str = field(default="", repr=False)

    def __post_init__(self):
        # 生成链接唯一标识
        link = self.pan_link or self.original_link
        if link:
            self._link_hash = hashlib.md5(link.encode()).hexdigest()

class BaseCollector(ABC):
    """采集器基类"""
    
    def __init__(self, cookie: str, name: str):
        self.cookie = cookie
        self.name = name
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Cookie': self.cookie
        })
    
    @abstractmethod
    def extract_links(self, html: str) -> List[Dict]:
        """从 HTML 中提取网盘链接"""
        pass
    
    def collect_from_source(self, source_url: str) -> List[Resource]:
        """从指定来源采集资源"""
        resources = []
        try:
            resp = self.session.get(source_url, timeout=30)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding or 'utf-8'
            links = self.extract_links(resp.text)
            
            for link_info in links:
                # 确保URL不为空
                url = link_info.get('url', '')
                if not url:
                    continue
                    
                resource = Resource(
                    title=link_info.get('title', '未知资源')[:200],  # 限制标题长度
                    pan_type=self.name.lower(),
                    pan_link=url,  # 原始链接保存到pan_link
                    description=link_info.get('desc', '')[:500]  # 限制描述长度
                )
                resources.append(resource)
                
            print(f"  [{self.name}] 从 {source_url} 采集到 {len(links)} 个链接")
            self._log(f"采集成功: {source_url}, 获取 {len(links)} 个链接")
            
        except requests.exceptions.Timeout:
            print(f"  [{self.name}] 采集超时: {source_url}")
            self._log(f"采集超时: {source_url}", level="WARNING")
        except requests.exceptions.RequestException as e:
            print(f"  [{self.name}] 采集失败: {e}")
            self._log(f"采集失败: {source_url}, 错误: {e}", level="ERROR")
        except Exception as e:
            print(f"  [{self.name}] 未知错误: {e}")
            self._log(f"未知错误: {source_url}, 错误: {e}", level="ERROR")
            
        return resources
    
    def _log(self, message: str, level: str = "INFO"):
        """写入日志"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] [{level}] [{self.name}] {message}\n"
        try:
            os.makedirs('logs', exist_ok=True)
            with open('logs/collector.log', 'a', encoding='utf-8') as f:
                f.write(log_entry)
        except Exception:
            pass

class QuarkeCollector(BaseCollector):
    """夸克网盘采集器"""
    def __init__(self): super().__init__(QUARKE_COOKIE, '夸克')
    
    def extract_links(self, html: str) -> List[Dict]:
        links = []
        seen = set()
        patterns = [
            r'quark\.cn/s/([a-zA-Z0-9]+)',
            r'pan\.quark\.cn/s/([a-zA-Z0-9]+)',
            r'pf\.stevenjack\.cn/s/([a-zA-Z0-9]+)',  # 第三方分享域名
        ]
        for pattern in patterns:
            for match in re.findall(pattern, html):
                if match not in seen:
                    seen.add(match)
                    # 提取分享标题（如果有）
                    title_match = re.search(rf'{match}[^<>]{{0,50}}(?:title[:\s]+["\']?([^"\'<\s]+))?', html)
                    title = title_match.group(1) if title_match and title_match.group(1) else f'夸克资源_{match[:8]}'
                    links.append({
                        'title': title,
                        'url': f'https://pan.quark.cn/s/{match}',
                        'desc': '夸克网盘资源'
                    })
        return links

class BaiduCollector(BaseCollector):
    """百度网盘采集器"""
    def __init__(self): super().__init__(BAIDU_COOKIE, '百度')
    
    def extract_links(self, html: str) -> List[Dict]:
        links = []
        seen = set()
        for match in re.findall(r'pan\.baidu\.com/s/([a-zA-Z0-9_-]+)', html):
            if match not in seen:
                seen.add(match)
                links.append({
                    'title': f'百度资源_{match[:8]}',
                    'url': f'https://pan.baidu.com/s/{match}',
                    'desc': '百度网盘资源'
                })
        return links

class UCCollector(BaseCollector):
    """UC网盘采集器"""
    def __init__(self): super().__init__(UC_COOKIE, 'UC')
    
    def extract_links(self, html: str) -> List[Dict]:
        links = []
        seen = set()
        patterns = [
            r'yun\.uc\.cn/([a-zA-Z0-9]+)',
            r'drive\.uc\.cn/([a-zA-Z0-9]+)',
            r'link\.uc\.cn/([a-zA-Z0-9]+)',
        ]
        for pattern in patterns:
            for match in re.findall(pattern, html):
                if match not in seen:
                    seen.add(match)
                    links.append({
                        'title': f'UC资源_{match[:8]}',
                        'url': f'https://drive.uc.cn/{match}',
                        'desc': 'UC网盘资源'
                    })
        return links

class XLCollector(BaseCollector):
    """迅雷网盘采集器"""
    def __init__(self): super().__init__(XL_COOKIE, '迅雷')
    
    def extract_links(self, html: str) -> List[Dict]:
        links = []
        seen = set()
        for match in re.findall(r'pan\.xunlei\.com/([a-zA-Z0-9_-]+)', html):
            if match not in seen:
                seen.add(match)
                links.append({
                    'title': f'迅雷资源_{match[:8]}',
                    'url': f'https://pan.xunlei.com/{match}',
                    'desc': '迅雷网盘资源'
                })
        return links

class KdocsCollector(BaseCollector):
    """Kdocs采集器 - 使用Playwright处理JS渲染"""
    
    def __init__(self):
        self.name = 'Kdocs'
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def extract_links(self, html: str) -> List[Dict]:
        """Kdocs页面需要JS渲染，使用简单的正则提取"""
        links = []
        seen = set()
        patterns = [
            r'kdocs\.cn/l/([a-zA-Z0-9]+)',
            r'www\.kdocs\.cn/l/([a-zA-Z0-9]+)',
        ]
        for pattern in patterns:
            for match in re.findall(pattern, html):
                if match not in seen:
                    seen.add(match)
                    links.append({
                        'title': f'Kdocs文档_{match[:8]}',
                        'url': f'https://www.kdocs.cn/l/{match}',
                        'desc': 'Kdocs在线文档'
                    })
        return links
    
    def collect_from_source(self, source_url: str) -> List:
        """采集Kdocs链接（静态提取，不需要JS渲染）"""
        resources = []
        try:
            resp = self.session.get(source_url, timeout=30)
            resp.raise_for_status()
            resp.encoding = 'utf-8'
            links = self.extract_links(resp.text)
            
            for link_info in links:
                url = link_info.get('url', '')
                if not url:
                    continue
                    
                resource = Resource(
                    title=link_info.get('title', '未知资源')[:200],
                    pan_type='kdocs',
                    pan_link=url,
                    description=link_info.get('desc', '')[:500]
                )
                resources.append(resource)
                
            print(f"  [Kdocs] 从 {source_url} 采集到 {len(links)} 个链接")
            
        except Exception as e:
            print(f"  [Kdocs] 采集失败: {e}")
            
        return resources

class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self):
        self.url = SUPABASE_URL
        self.key = SUPABASE_KEY
        self.headers = {
            'apikey': self.key,
            'Authorization': f'Bearer {self.key}',
            'Content-Type': 'application/json',
            'Prefer': 'return=representation'
        }
    
    def check_exists(self, pan_link: str) -> Optional[Dict]:
        """检查资源是否已存在"""
        try:
            # URL编码pan_link
            encoded_link = urllib.parse.quote(pan_link, safe='')
            check_url = f"{self.url}/rest/v1/resources?pan_link=eq.{encoded_link}&select=id,title"
            resp = requests.get(check_url, headers=self.headers, timeout=10)
            
            if resp.status_code == 200:
                result = resp.json()
                return result[0] if result else None
            else:
                print(f"  ⚠️ 检查重复失败: HTTP {resp.status_code}")
                return None
        except Exception as e:
            print(f"  ⚠️ 检查重复异常: {e}")
            return None
    
    def save_resource(self, resource: Resource) -> bool:
        """保存资源到数据库"""
        # Bug修复: 确保pan_link不为空
        if not resource.pan_link:
            print(f"  ⚠️ 链接为空，跳过: {resource.title}")
            return False
        
        try:
            # 检查是否已存在
            existing = self.check_exists(resource.pan_link)
            if existing:
                print(f"  ⏭️ 资源已存在，跳过: {existing.get('title', resource.title)}")
                return False
            
            # 插入新资源（与 Supabase resources 表完全匹配）
            data = {
                'title': resource.title,
                'description': resource.description or '',
                'category': self._detect_category(resource.title),
                'pan_link': resource.pan_link,
                'extract_code': resource.extract_code or '',
                'views': 0,
                'created_at': datetime.now().isoformat()
            }
            
            insert_url = f"{self.url}/rest/v1/resources"
            resp = requests.post(insert_url, headers=self.headers, json=data, timeout=15)
            
            if resp.status_code in [200, 201]:
                result = resp.json()
                saved_id = result[0].get('id', 'N/A') if result else 'N/A'
                print(f"  ✅ 保存成功 [{saved_id}]: {resource.title}")
                return True
            else:
                print(f"  ❌ 保存失败 [{resp.status_code}]: {resp.text[:200]}")
                return False
                
        except requests.exceptions.Timeout:
            print(f"  ❌ 保存超时: {resource.title}")
            return False
        except Exception as e:
            print(f"  ❌ 数据库错误: {e}")
            return False
    
    def _detect_category(self, title: str) -> str:
        """根据标题自动分类"""
        t = title.lower()
        cats = {
            '短剧': ['短剧', '短片', '微剧', '剧情', '网剧', '甜剧', '虐剧', '爽剧'],
            '教程': ['教程', '课程', '学习', '教学', '培训', '讲解', '入门', '进阶'],
            '软件': ['软件', '工具', 'app', '程序', '破解', '绿色版', '免安装'],
            '素材': ['素材', '模板', '背景', '音乐', '音效', '配乐', '片头', '片尾'],
            '文档': ['文档', 'pdf', '电子书', '书籍', '小说', '漫画', '文档', '资料']
        }
        for cat, words in cats.items():
            if any(w in t for w in words):
                return cat
        return '其他'

class CollectorSystem:
    """采集系统主控制器"""
    
    def __init__(self):
        self.collectors = [
            QuarkeCollector(),
            BaiduCollector(),
            UCCollector(),
            XLCollector(),
            KdocsCollector()
        ]
        self.db = DatabaseManager()
        # Bug修复: 添加全局去重集合
        self.seen_links: Set[str] = set()
        self.results = {
            'total': 0, 
            'success': 0, 
            'failed': 0, 
            'skipped': 0,
            'duplicates': 0
        }
        self.start_time = None
        
    def _deduplicate(self, resource: Resource) -> bool:
        """去重检查，返回True表示需要处理"""
        link = resource.pan_link or resource.original_link
        link_hash = hashlib.md5(link.encode()).hexdigest() if link else ""

        if link_hash in self.seen_links:
            self.results['duplicates'] += 1
            return False
        
        self.seen_links.add(link_hash)
        return True
    
    def run(self):
        """执行采集任务"""
        self.start_time = datetime.now()
        
        print("=" * 60)
        print("🚀 每日资源采集系统 v2.1 启动")
        print(f"⏰ 开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📡 采集源数量: {len(COLLECT_SOURCES)}")
        print("=" * 60)
        
        # 初始化日志
        self._init_log()
        self._log("采集任务开始")
        
        all_resources = []
        
        # 从各来源采集
        for source in COLLECT_SOURCES:
            print(f"\n📡 正在采集: {source}")
            self._log(f"开始采集: {source}")
            
            for collector in self.collectors:
                resources = collector.collect_from_source(source)
                # Bug修复: 去重
                for r in resources:
                    if self._deduplicate(r):
                        all_resources.append(r)
                    else:
                        self.results['duplicates'] += 1
            
            # 随机延时，避免请求过快
            time.sleep(random.uniform(2, 5))
        
        # 计算采集到的资源总数
        total_found = len(all_resources) + self.results['duplicates']
        print(f"\n📊 采集完成:")
        print(f"   - 采集到链接: {total_found}")
        print(f"   - 去重后: {len(all_resources)}")
        print(f"   - 重复跳过: {self.results['duplicates']}")
        
        self._log(f"采集完成，共获取 {len(all_resources)} 个有效链接")
        
        # 处理每个资源
        print("\n💾 开始保存到数据库...")
        for r in all_resources:
            self.results['total'] += 1
            
            # Bug修复: 确保pan_link有值
            r.pan_link = r.pan_link or r.original_link
            r.extract_code = EXTRACT_CODE if EXTRACT_CODE else None
            
            if self.db.save_resource(r):
                self.results['success'] += 1
            else:
                self.results['skipped'] += 1
            
            # 随机延时
            time.sleep(random.uniform(0.5, 1.5))
        
        # 计算耗时
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        # 输出统计
        print("\n" + "=" * 60)
        print("📊 采集任务完成")
        print(f"   ⏱️  耗时: {duration:.1f} 秒")
        print(f"   📥 总计处理: {self.results['total']}")
        print(f"   ✅ 成功入库: {self.results['success']}")
        print(f"   ⏭️  跳过/重复: {self.results['skipped'] + self.results['duplicates']}")
        print(f"   ❌ 失败: {self.results['failed']}")
        print("=" * 60)
        
        # Bug修复: 保存详细统计信息
        self._save_stats(duration)
        self._log(f"任务完成: 成功{self.results['success']}, 跳过{self.results['skipped']}")
    
    def _init_log(self):
        """初始化日志文件"""
        os.makedirs('logs', exist_ok=True)
        with open('logs/collector.log', 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*50}\n")
    
    def _log(self, message: str, level: str = "INFO"):
        """写入日志"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] [{level}] {message}\n"
        try:
            os.makedirs('logs', exist_ok=True)
            with open('logs/collector.log', 'a', encoding='utf-8') as f:
                f.write(log_entry)
        except Exception:
            pass
    
    def _save_stats(self, duration: float):
        """保存统计信息到文件"""
        stats = {
            'version': '2.1',
            'timestamp': self.start_time.isoformat(),
            'duration_seconds': duration,
            'sources': COLLECT_SOURCES,
            'results': self.results,
            'collectors': [c.name for c in self.collectors]
        }
        
        os.makedirs('logs', exist_ok=True)
        filename = f"logs/collect_{self.start_time.strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        
        print(f"📁 日志已保存: {filename}")

if __name__ == '__main__':
    CollectorSystem().run()

# ==================== 使用说明 ====================
# 
# 1. 手动运行:
#    python collector.py
#
# 2. GitHub Actions 自动运行:
#    - 每天北京时间 9:00 (UTC 1:00) 自动执行
#    - 可在 GitHub Actions 页面手动触发
#
# 3. 支持通过 curl 手动触发:
#    curl -X POST https://api.github.com/repos/lvzengqin-cmd/resource-collector/dispatches \
#      -H "Accept: application/vnd.github+json" \
#      -H "Authorization: token YOUR_TOKEN" \
#      -d '{"event_type": "manual-collection"}'
