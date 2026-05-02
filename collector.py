#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
资源采集脚本 - 自动化采集网盘资源
由 GitHub Actions 定时触发
"""

import os
import re
import json
import time
import logging
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from urllib.parse import urlparse

# 导入Supabase客户端
from supabase import create_client, Client

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('collector.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Supabase配置
SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://musrilmjolaquhnfqjdu.supabase.co')
SUPABASE_KEY = os.environ.get('SUPABASE_ANON_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im11c3JpbG1qb2xhcWhuZnFqZHVzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MTYyMzg3MDAsImV4cCI6MjAzMTgxNDcwMH0.gLl4KZJ6LK7sRBB5c8GJ4I0i_Xf6X8KQ8TqF6v6Q5r0')

@dataclass
class Resource:
    """资源数据类"""
    title: str
    description: str = ''
    pan_type: str = ''
    original_link: str = ''
    pan_link: str = ''
    extract_code: str = ''
    source_url: str = ''
    source_site: str = ''
    status: str = 'pending'
    views: int = 0

class SupabaseClient:
    """Supabase客户端"""
    
    def __init__(self):
        self.client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    def add_resource(self, resource: Resource) -> Optional[Dict]:
        """添加资源到数据库"""
        try:
            data = {
                'title': resource.title,
                'description': resource.description,
                'pan_type': resource.pan_type,
                'original_link': resource.original_link,
                'pan_link': resource.pan_link,
                'extract_code': resource.extract_code,
                'source_url': resource.source_url,
                'source_site': resource.source_site,
                'status': resource.status,
                'views': resource.views
            }
            
            result = self.client.table('resources').insert(data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"添加资源失败: {e}")
            return None
    
    def add_resources_batch(self, resources: List[Resource]) -> int:
        """批量添加资源"""
        count = 0
        for resource in resources:
            if self.add_resource(resource):
                count += 1
        return count
    
    def get_resources(self, limit: int = 100) -> List[Dict]:
        """获取资源列表"""
        try:
            result = self.client.table('resources').select('*').limit(limit).execute()
            return result.data
        except Exception as e:
            logger.error(f"获取资源失败: {e}")
            return []
    
    def update_resource_status(self, id: int, status: str) -> bool:
        """更新资源状态"""
        try:
            self.client.table('resources').update({
                'status': status,
                'updated_at': datetime.now().isoformat()
            }).eq('id', id).execute()
            return True
        except Exception as e:
            logger.error(f"更新状态失败: {e}")
            return False

class PanLinkExtractor:
    """网盘链接提取器"""
    
    # 网盘域名匹配
    PAN_PATTERNS = {
        'quark': [
            r'pan\.quark\.cn/s/([a-zA-Z0-9]+)',
            r'quark\.cn/s/([a-zA-Z0-9]+)',
        ],
        'baidu': [
            r'pan\.baidu\.com/s/([a-zA-Z0-9_-]+)',
            r'baidu\.com/s/([a-zA-Z0-9_-]+)',
        ],
        'uc': [
            r'drive\.uc\.cn/s/([a-zA-Z0-9]+)',
            r'uc\.cn/s/([a-zA-Z0-9]+)',
        ],
        'thunder': [
            r'pan\.xunlei\.com/s/([a-zA-Z0-9]+)',
            r'xunlei\.com/s/([a-zA-Z0-9]+)',
        ],
    }
    
    # 提取码匹配
    PWD_PATTERN = r'[?&]pwd=([a-zA-Z0-9]{4})|提取码[：:]\s*([a-zA-Z0-9]{4})'
    
    @classmethod
    def detect_pan_type(cls, url: str) -> Optional[str]:
        """检测网盘类型"""
        url_lower = url.lower()
        
        if 'quark.cn' in url_lower or 'pan.quark' in url_lower:
            return 'quark'
        elif 'baidu.com' in url_lower or 'pan.baidu' in url_lower:
            return 'baidu'
        elif 'uc.cn' in url_lower or 'drive.uc' in url_lower:
            return 'uc'
        elif 'xunlei.com' in url_lower or 'pan.xunlei' in url_lower:
            return 'thunder'
        
        return None
    
    @classmethod
    def extract_link(cls, text: str) -> List[Dict]:
        """从文本中提取所有网盘链接"""
        results = []
        
        # 清理URL
        urls = re.findall(r'https?://[^\s<>"\')\]]+', text)
        
        for url in urls:
            pan_type = cls.detect_pan_type(url)
            if not pan_type:
                continue
            
            # 清理URL
            clean_url = url.split('?')[0].rstrip('/')
            
            # 提取码
            pwd_match = re.search(cls.PWD_PATTERN, text)
            pwd = pwd_match.group(1) or pwd_match.group(2) if pwd_match else ''
            
            results.append({
                'url': clean_url,
                'pan_type': pan_type,
                'pwd': pwd
            })
        
        return results
    
    @classmethod
    def extract_from_content(cls, title: str, content: str) -> Optional[Resource]:
        """从内容中提取资源信息"""
        links = cls.extract_link(content)
        
        if not links:
            return None
        
        # 使用第一个链接作为主链接
        link_info = links[0]
        
        # 清理标题
        clean_title = title.strip() if title else content.split('\n')[0][:100]
        
        return Resource(
            title=clean_title,
            description=content[:500],
            pan_type=link_info['pan_type'],
            original_link=link_info['url'],
            extract_code=link_info['pwd'],
            source_site='auto_collect'
        )

class ResourceCollector:
    """资源采集器"""
    
    # 默认采集源
    DEFAULT_SOURCES = [
        {
            'name': 'Lsfa影视',
            'url': 'http://ys2.lsfa.site/',
            'type': 'auto'
        },
        {
            'name': 'Lsfa短剧',
            'url': 'http://dj.lsfa.site/',
            'type': 'auto'
        },
    ]
    
    def __init__(self, db_client: SupabaseClient):
        self.db = db_client
    
    def fetch_page(self, url: str) -> Optional[str]:
        """获取页面内容"""
        try:
            import requests
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            response.encoding = response.apparent_encoding
            
            return response.text
        except Exception as e:
            logger.error(f"获取页面失败 {url}: {e}")
            return None
    
    def parse_page(self, html: str, source_name: str) -> List[Resource]:
        """解析页面提取资源"""
        resources = []
        
        try:
            from bs4 import BeautifulSoup
            
            soup = BeautifulSoup(html, 'lxml')
            
            # 查找资源列表（通用模式）
            items = soup.select('.resource-item, .item, article, .post, .entry')
            
            for item in items[:20]:  # 限制每页采集数量
                # 提取标题
                title_elem = item.select_one('h2, h3, .title, a')
                title = title_elem.get_text(strip=True) if title_elem else ''
                
                # 提取链接
                link = item.select_one('a')
                href = link.get('href', '') if link else ''
                
                # 完整URL
                if href and not href.startswith('http'):
                    from urllib.parse import urljoin
                    href = urljoin(source_name, href)
                
                # 提取内容文本
                content = item.get_text(strip=True)[:1000]
                
                # 提取资源
                resource = PanLinkExtractor.extract_from_content(title, content + ' ' + href)
                
                if resource:
                    resource.source_site = source_name
                    resources.append(resource)
            
            # 备用解析：直接从HTML中查找网盘链接
            direct_links = PanLinkExtractor.extract_link(html)
            for link_info in direct_links:
                resource = Resource(
                    title=f"资源_{link_info['pan_type']}_{datetime.now().strftime('%Y%m%d%H%M')}",
                    pan_type=link_info['pan_type'],
                    original_link=link_info['url'],
                    extract_code=link_info['pwd'],
                    source_site=source_name
                )
                resources.append(resource)
            
        except Exception as e:
            logger.error(f"解析页面失败: {e}")
        
        return resources
    
    def collect_from_source(self, source: Dict) -> int:
        """从指定源采集"""
        logger.info(f"开始采集: {source['name']} - {source['url']}")
        
        html = self.fetch_page(source['url'])
        if not html:
            return 0
        
        resources = self.parse_page(html, source['name'])
        
        if not resources:
            logger.info(f"未从 {source['name']} 发现新资源")
            return 0
        
        # 去重后添加
        added = self.db.add_resources_batch(resources)
        logger.info(f"从 {source['name']} 添加了 {added} 个资源")
        
        return added
    
    def run(self, sources: List[Dict] = None) -> Dict:
        """执行采集任务"""
        start_time = datetime.now()
        logger.info("=" * 50)
        logger.info("开始执行采集任务")
        logger.info("=" * 50)
        
        if sources is None:
            sources = self.DEFAULT_SOURCES
        
        total_added = 0
        results = {
            'sources': {},
            'total_added': 0,
            'start_time': start_time.isoformat(),
            'end_time': None,
            'duration': 0
        }
        
        for source in sources:
            try:
                count = self.collect_from_source(source)
                results['sources'][source['name']] = count
                total_added += count
            except Exception as e:
                logger.error(f"采集 {source['name']} 失败: {e}")
                results['sources'][source['name']] = 0
        
        end_time = datetime.now()
        results['end_time'] = end_time.isoformat()
        results['duration'] = (end_time - start_time).total_seconds()
        results['total_added'] = total_added
        
        logger.info("=" * 50)
        logger.info(f"采集完成! 共添加 {total_added} 个资源")
        logger.info(f"耗时: {results['duration']:.2f} 秒")
        logger.info("=" * 50)
        
        return results


def main():
    """主入口"""
    task_type = os.environ.get('TASK_TYPE', 'all')
    logger.info(f"任务类型: {task_type}")
    
    # 初始化数据库
    db = SupabaseClient()
    
    # 执行采集
    collector = ResourceCollector(db)
    results = collector.run()
    
    # 保存结果到日志
    with open('collection_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    logger.info(f"结果已保存: {results}")
    
    return results


if __name__ == '__main__':
    main()
