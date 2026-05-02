#!/usr/bin/env python3
"""
每日资源采集系统 v2.0
支持夸克、百度、UC、迅雷网盘的自动化采集
"""

import os
import re
import json
import time
import random
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod
import requests

from config import (
    SUPABASE_URL, SUPABASE_KEY,
    QUARKE_COOKIE, BAIDU_COOKIE, UC_COOKIE, XL_COOKIE,
    TRANSFER_DIR, AUTO_SHARE, SHARE_EXPIRE, EXTRACT_CODE,
    COLLECT_SOURCES
)

@dataclass
class Resource:
    """资源数据模型"""
    title: str
    pan_type: str
    original_link: str
    pan_link: Optional[str] = None
    extract_code: Optional[str] = None
    description: Optional[str] = None
    status: str = "pending"
    views: int = 0

class BaseCollector(ABC):
    """采集器基类"""
    
    def __init__(self, cookie: str, name: str):
        self.cookie = cookie
        self.name = name
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
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
            links = self.extract_links(resp.text)
            for link_info in links:
                resource = Resource(
                    title=link_info.get('title', '未知资源'),
                    pan_type=self.name.lower(),
                    original_link=link_info.get('url', ''),
                    description=link_info.get('desc', '')
                )
                resources.append(resource)
            print(f"  [{self.name}] 从 {source_url} 采集到 {len(links)} 个链接")
        except Exception as e:
            print(f"  [{self.name}] 采集失败: {e}")
        return resources

class QuarkeCollector(BaseCollector):
    """夸克网盘采集器"""
    def __init__(self): super().__init__(QUARKE_COOKIE, '夸克')
    def extract_links(self, html: str) -> List[Dict]:
        links = []
        patterns = [
            r'quark\.cn/s/([a-zA-Z0-9]+)',
            r'pan\.quark\.cn/s/([a-zA-Z0-9]+)',
        ]
        for pattern in patterns:
            for match in re.findall(pattern, html):
                links.append({
                    'title': f'夸克资源_{match[:8]}',
                    'url': f'https://pan.quark.cn/s/{match}',
                    'desc': '夸克网盘资源'
                })
        return links

class BaiduCollector(BaseCollector):
    """百度网盘采集器"""
    def __init__(self): super().__init__(BAIDU_COOKIE, '百度')
    def extract_links(self, html: str) -> List[Dict]:
        links = []
        for match in re.findall(r'pan\.baidu\.com/s/([a-zA-Z0-9_-]+)', html):
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
        for pattern in [r'yun\.uc\.cn/([a-zA-Z0-9]+)', r'drive\.uc\.cn/([a-zA-Z0-9]+)']:
            for match in re.findall(pattern, html):
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
        for match in re.findall(r'pan\.xunlei\.com/([a-zA-Z0-9_-]+)', html):
            links.append({
                'title': f'迅雷资源_{match[:8]}',
                'url': f'https://pan.xunlei.com/{match}',
                'desc': '迅雷网盘资源'
            })
        return links

class DatabaseManager:
    """数据库管理器"""
    def __init__(self):
        self.url = SUPABASE_URL
        self.key = SUPABASE_KEY
        self.headers = {
            'apikey': self.key,
            'Authorization': f'Bearer {self.key}',
            'Content-Type': 'application/json'
        }
    
    def save_resource(self, resource: Resource) -> bool:
        """保存资源到数据库"""
        try:
            # 检查是否已存在
            check_url = f"{self.url}/rest/v1/resources?pan_link=eq.{resource.pan_link}&select=id"
            resp = requests.get(check_url, headers=self.headers)
            if resp.json():
                print(f"  ⏭️ 资源已存在，跳过: {resource.title}")
                return False
            
            # 插入新资源
            data = {
                'title': resource.title,
                'description': resource.description or '',
                'category': self._detect_category(resource.title),
                'pan_link': resource.pan_link,
                'extract_code': resource.extract_code,
                'views': 0,
                'created_at': datetime.now().isoformat()
            }
            
            insert_url = f"{self.url}/rest/v1/resources"
            resp = requests.post(insert_url, headers=self.headers, json=data)
            
            if resp.status_code in [200, 201]:
                print(f"  ✅ 保存成功: {resource.title}")
                return True
            print(f"  ❌ 保存失败: {resp.text[:100]}")
            return False
        except Exception as e:
            print(f"  ❌ 数据库错误: {e}")
            return False
    
    def _detect_category(self, title: str) -> str:
        """根据标题自动分类"""
        t = title.lower()
        cats = {
            '短剧': ['短剧', '短片', '微剧', '剧情'],
            '教程': ['教程', '课程', '学习', '教学'],
            '软件': ['软件', '工具', 'app', '程序'],
            '素材': ['素材', '模板', '背景', '音乐'],
            '文档': ['文档', 'pdf', '电子书', '书籍']
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
            XLCollector()
        ]
        self.db = DatabaseManager()
        self.results = {'total': 0, 'success': 0, 'failed': 0, 'skipped': 0}
    
    def run(self):
        """执行采集任务"""
        print("=" * 60)
        print("🚀 每日资源采集系统启动")
        print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        all_resources = []
        
        # 从各来源采集
        for source in COLLECT_SOURCES:
            print(f"\n📡 正在采集: {source}")
            for collector in self.collectors:
                resources = collector.collect_from_source(source)
                all_resources.extend(resources)
            # 随机延时
            time.sleep(random.uniform(1, 3))
        
        print(f"\n📊 采集完成，共获取 {len(all_resources)} 个链接")
        
        # 处理每个资源
        for r in all_resources:
            self.results['total'] += 1
            r.pan_link = r.original_link
            r.extract_code = EXTRACT_CODE if EXTRACT_CODE else None
            
            if self.db.save_resource(r):
                self.results['success'] += 1
            else:
                self.results['skipped'] += 1
            
            time.sleep(random.uniform(0.5, 1.5))
        
        # 输出统计
        print("\n" + "=" * 60)
        print("📊 采集任务完成")
        print(f"   总计处理: {self.results['total']}")
        print(f"   ✅ 成功: {self.results['success']}")
        print(f"   ⏭️  跳过: {self.results['skipped']}")
        print(f"   ❌ 失败: {self.results['failed']}")
        print("=" * 60)
        
        # 保存日志
        os.makedirs('logs', exist_ok=True)
        with open(f"logs/collect_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'results': self.results
            }, f, ensure_ascii=False, indent=2)

if __name__ == '__main__':
    CollectorSystem().run()

# 支持通过 curl 手动触发:
# curl -X POST https://api.github.com/repos/lvzengqin-cmd/resource-collector/dispatches \
#   -H "Accept: application/vnd.github+json" \
#   -H "Authorization: token YOUR_TOKEN" \
#   -d '{"event_type": "manual-collection"}'
