#!/usr/bin/env python3
"""
网盘自动转存模块 v1.0
使用 Playwright 自动化浏览器操作，实现网盘资源转存

功能：
1. 夸克网盘自动转存
2. 百度网盘自动转存
3. 转存后生成分享链接

注意：此模块需要较长的运行时间，建议在本地测试后再部署到GitHub Actions
"""

import os
import sys
import json
import time
import random
from datetime import datetime
from typing import Optional, Dict, List
from dataclasses import dataclass, field

# 导入配置
from config import (
    QUARKE_COOKIE, BAIDU_COOKIE, UC_COOKIE, XL_COOKIE,
    TRANSFER_DIR, AUTO_SHARE, SHARE_EXPIRE
)

# Playwright
try:
    from playwright.sync_api import sync_playwright, Browser, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("⚠️ Playwright 未安装，请运行: pip install playwright && playwright install chromium")


@dataclass
class TransferResult:
    """转存结果"""
    success: bool
    original_link: str
    share_link: Optional[str] = None
    extract_code: Optional[str] = None
    error: Optional[str] = None
    platform: str = ""
    duration: float = 0


@dataclass
class Resource:
    """需要转存的资源"""
    title: str
    pan_type: str
    pan_link: str
    extract_code: Optional[str] = None
    description: Optional[str] = None


class BaseTransfer:
    """转存基类"""
    
    def __init__(self, cookie: str, platform: str):
        self.cookie = cookie
        self.platform = platform
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        
    def close(self):
        """关闭浏览器"""
        if self.browser:
            self.browser.close()
            
    def init_browser(self) -> bool:
        """初始化浏览器"""
        if not PLAYWRIGHT_AVAILABLE:
            print(f"❌ [{self.platform}] Playwright 不可用")
            return False
            
        try:
            playwright = sync_playwright().start()
            self.browser = playwright.chromium.launch(
                headless=True,  # 无头模式
                args=['--disable-blink-features=AutomationControlled']
            )
            self.page = self.browser.new_page(
                viewport={'width': 1920, 'height': 1080}
            )
            # 设置 User-Agent
            self.page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            print(f"✅ [{self.platform}] 浏览器初始化成功")
            return True
        except Exception as e:
            print(f"❌ [{self.platform}] 浏览器初始化失败: {e}")
            return False
            
    def set_cookie(self) -> bool:
        """设置Cookie"""
        raise NotImplementedError
        
    def transfer(self, resource: Resource) -> TransferResult:
        """执行转存"""
        raise NotImplementedError
        
    def get_share_link(self) -> tuple:
        """获取分享链接"""
        raise NotImplementedError


class QuarkeTransfer(BaseTransfer):
    """夸克网盘转存"""
    
    BASE_URL = "https://pan.quark.cn"
    
    def __init__(self, cookie: str = None):
        super().__init__(cookie or QUARKE_COOKIE, "夸克")
        
    def set_cookie(self) -> bool:
        """设置夸克Cookie"""
        try:
            self.page.goto(self.BASE_URL, wait_until="networkidle", timeout=30000)
            time.sleep(random.uniform(1, 2))
            
            # 解析Cookie字符串
            cookies = []
            for item in self.cookie.split(';'):
                item = item.strip()
                if '=' in item:
                    name, value = item.split('=', 1)
                    cookies.append({
                        'name': name.strip(),
                        'value': value.strip(),
                        'domain': '.quark.cn',
                        'path': '/'
                    })
            
            if cookies:
                self.page.context.add_cookies(cookies)
                print(f"✅ [{self.platform}] Cookie设置成功")
                return True
            return False
        except Exception as e:
            print(f"❌ [{self.platform}] Cookie设置失败: {e}")
            return False
            
    def check_login(self) -> bool:
        """检查登录状态"""
        try:
            self.page.goto(f"{self.BASE_URL}/space/list", wait_until="networkidle", timeout=30000)
            time.sleep(2)
            
            # 检查是否已登录（通过是否存在用户信息）
            content = self.page.content()
            if "登录" in content or "login" in content.lower():
                print(f"⚠️ [{self.platform}] 未登录或登录已过期")
                return False
            return True
        except Exception as e:
            print(f"❌ [{self.platform}] 登录检查失败: {e}")
            return False
            
    def transfer(self, resource: Resource) -> TransferResult:
        """夸克网盘转存"""
        start_time = time.time()
        
        try:
            print(f"\n📦 [{self.platform}] 开始转存: {resource.title}")
            
            # 1. 访问分享页面
            share_url = resource.pan_link
            if not share_url.startswith('http'):
                share_url = f"https://pan.quark.cn/s/{share_url}"
                
            print(f"   访问: {share_url}")
            self.page.goto(share_url, wait_until="networkidle", timeout=60000)
            time.sleep(random.uniform(2, 4))
            
            # 2. 点击转存按钮
            try:
                # 尝试点击转存按钮（选择器可能需要调整）
                transfer_btn = self.page.locator('button:has-text("转存")').first
                if transfer_btn.is_visible(timeout=5000):
                    transfer_btn.click()
                    time.sleep(2)
                    print(f"   ✅ 点击转存按钮")
                else:
                    # 尝试其他选择器
                    transfer_btn = self.page.locator('.transfer-btn, [class*="save"], button:has-text("保存")').first
                    if transfer_btn.is_visible(timeout=3000):
                        transfer_btn.click()
                        time.sleep(2)
                        print(f"   ✅ 点击保存按钮")
            except Exception as e:
                print(f"   ⚠️ 未找到转存按钮: {e}")
                
            # 3. 选择目标文件夹
            try:
                # 选择目标文件夹
                folder_input = self.page.locator('input[placeholder*="目录"], input[placeholder*="文件夹"]').first
                if folder_input.is_visible(timeout=3000):
                    folder_input.fill(TRANSFER_DIR)
                    time.sleep(1)
                    print(f"   📁 选择目录: {TRANSFER_DIR}")
            except:
                pass
                
            # 4. 确认转存
            try:
                confirm_btn = self.page.locator('button:has-text("确定"), button:has-text("确认")').first
                if confirm_btn.is_visible(timeout=3000):
                    confirm_btn.click()
                    time.sleep(2)
                    print(f"   ✅ 确认转存")
            except:
                pass
                
            # 5. 获取分享链接
            share_link, extract_code = self.get_share_link()
            
            duration = time.time() - start_time
            return TransferResult(
                success=True,
                original_link=resource.pan_link,
                share_link=share_link,
                extract_code=extract_code,
                platform="夸克",
                duration=duration
            )
            
        except Exception as e:
            duration = time.time() - start_time
            return TransferResult(
                success=False,
                original_link=resource.pan_link,
                error=str(e),
                platform="夸克",
                duration=duration
            )
            
    def get_share_link(self) -> tuple:
        """获取分享链接"""
        try:
            # 访问网盘获取分享功能
            self.page.goto(f"{self.BASE_URL}/space/list", wait_until="networkidle", timeout=30000)
            time.sleep(2)
            
            # 点击分享按钮
            try:
                share_btn = self.page.locator('button:has-text("分享")').first
                if share_btn.is_visible(timeout=5000):
                    share_btn.click()
                    time.sleep(2)
                    
                    # 获取分享链接
                    link_input = self.page.locator('input[readonly], input[value*="quark"]').first
                    if link_input.is_visible(timeout=3000):
                        share_link = link_input.get_attribute('value') or link_input.input_value()
                        return share_link, None
            except:
                pass
                
            return None, None
        except Exception as e:
            print(f"⚠️ 获取分享链接失败: {e}")
            return None, None


class BaiduTransfer(BaseTransfer):
    """百度网盘转存"""
    
    BASE_URL = "https://pan.baidu.com"
    
    def __init__(self, cookie: str = None):
        super().__init__(cookie or BAIDU_COOKIE, "百度")
        
    def set_cookie(self) -> bool:
        """设置百度Cookie"""
        try:
            self.page.goto(self.BASE_URL, wait_until="networkidle", timeout=30000)
            time.sleep(random.uniform(1, 2))
            
            cookies = []
            for item in self.cookie.split(';'):
                item = item.strip()
                if '=' in item:
                    name, value = item.split('=', 1)
                    cookies.append({
                        'name': name.strip(),
                        'value': value.strip(),
                        'domain': '.baidu.com',
                        'path': '/'
                    })
            
            if cookies:
                self.page.context.add_cookies(cookies)
                print(f"✅ [{self.platform}] Cookie设置成功")
                return True
            return False
        except Exception as e:
            print(f"❌ [{self.platform}] Cookie设置失败: {e}")
            return False
            
    def check_login(self) -> bool:
        """检查登录状态"""
        try:
            self.page.goto(f"{self.BASE_URL}/disk/home", wait_until="networkidle", timeout=30000)
            time.sleep(2)
            
            content = self.page.content()
            if "登录" in content or "login" in content.lower():
                print(f"⚠️ [{self.platform}] 未登录或登录已过期")
                return False
            return True
        except Exception as e:
            print(f"❌ [{self.platform}] 登录检查失败: {e}")
            return False
            
    def transfer(self, resource: Resource) -> TransferResult:
        """百度网盘转存"""
        start_time = time.time()
        
        try:
            print(f"\n📦 [{self.platform}] 开始转存: {resource.title}")
            
            share_url = resource.pan_link
            if not share_url.startswith('http'):
                share_url = f"https://pan.baidu.com/s/{share_url}"
                
            print(f"   访问: {share_url}")
            self.page.goto(share_url, wait_until="networkidle", timeout=60000)
            time.sleep(random.uniform(2, 4))
            
            # 提取码
            extract_code = resource.extract_code or ""
            
            # 输入提取码
            if extract_code:
                try:
                    code_input = self.page.locator('input[name="pwd"]').first
                    if code_input.is_visible(timeout=3000):
                        code_input.fill(extract_code)
                        time.sleep(1)
                        
                        submit_btn = self.page.locator('button:has-text("提取")').first
                        if submit_btn.is_visible(timeout=3000):
                            submit_btn.click()
                            time.sleep(3)
                            print(f"   🔑 输入提取码: {extract_code}")
                except Exception as e:
                    print(f"   ⚠️ 输入提取码失败: {e}")
            
            # 点击转存
            try:
                transfer_btn = self.page.locator('button:has-text("转存"), button:has-text("存入百度网盘")').first
                if transfer_btn.is_visible(timeout=5000):
                    transfer_btn.click()
                    time.sleep(2)
                    print(f"   ✅ 点击转存按钮")
            except Exception as e:
                print(f"   ⚠️ 未找到转存按钮: {e}")
                
            duration = time.time() - start_time
            return TransferResult(
                success=True,
                original_link=resource.pan_link,
                extract_code=extract_code,
                platform="百度",
                duration=duration
            )
            
        except Exception as e:
            duration = time.time() - start_time
            return TransferResult(
                success=False,
                original_link=resource.pan_link,
                error=str(e),
                platform="百度",
                duration=duration
            )


def transfer_resource(resource: Resource) -> TransferResult:
    """转存单个资源"""
    pan_type = resource.pan_type.lower()
    
    if 'quark' in pan_type or '夸克' in pan_type:
        transfer = QuarkeTransfer()
    elif 'baidu' in pan_type or '百度' in pan_type:
        transfer = BaiduTransfer()
    else:
        return TransferResult(
            success=False,
            original_link=resource.pan_link,
            error=f"不支持的平台: {pan_type}",
            platform=pan_type
        )
    
    # 初始化浏览器
    if not transfer.init_browser():
        return TransferResult(
            success=False,
            original_link=resource.pan_link,
            error="浏览器初始化失败",
            platform=resource.pan_type
        )
    
    # 设置Cookie
    if not transfer.set_cookie():
        transfer.close()
        return TransferResult(
            success=False,
            original_link=resource.pan_link,
            error="Cookie设置失败",
            platform=resource.pan_type
        )
    
    # 检查登录
    if not transfer.check_login():
        transfer.close()
        return TransferResult(
            success=False,
            original_link=resource.pan_link,
            error="登录失败",
            platform=resource.pan_type
        )
    
    # 执行转存
    result = transfer.transfer(resource)
    transfer.close()
    
    return result


def batch_transfer(resources: List[Resource], delay: float = 5) -> List[TransferResult]:
    """批量转存"""
    results = []
    
    print(f"\n{'='*60}")
    print(f"📦 开始批量转存，共 {len(resources)} 个资源")
    print(f"{'='*60}")
    
    for i, resource in enumerate(resources, 1):
        print(f"\n[{i}/{len(resources)}] 处理中...")
        
        result = transfer_resource(resource)
        results.append(result)
        
        if result.success:
            print(f"   ✅ 成功")
        else:
            print(f"   ❌ 失败: {result.error}")
        
        # 间隔延时，避免频繁操作
        if i < len(resources):
            print(f"   ⏳ 等待 {delay} 秒...")
            time.sleep(delay)
    
    # 统计
    success_count = sum(1 for r in results if r.success)
    print(f"\n{'='*60}")
    print(f"📊 转存完成: {success_count}/{len(resources)} 成功")
    print(f"{'='*60}")
    
    return results


# ==================== 命令行接口 ====================

def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='网盘转存工具')
    parser.add_argument('--link', '-l', help='网盘链接')
    parser.add_argument('--title', '-t', help='资源标题')
    parser.add_argument('--type', default='夸克', help='网盘类型 (夸克/百度)')
    parser.add_argument('--code', '-c', help='提取码')
    parser.add_argument('--batch', '-b', help='批量文件 (JSON格式)')
    parser.add_argument('--delay', '-d', type=float, default=5, help='批量转存间隔(秒)')
    
    args = parser.parse_args()
    
    if not PLAYWRIGHT_AVAILABLE:
        print("❌ Playwright 不可用，请先安装: pip install playwright && playwright install chromium")
        sys.exit(1)
    
    # 单个转存
    if args.link:
        resource = Resource(
            title=args.title or "未命名资源",
            pan_type=args.type,
            pan_link=args.link,
            extract_code=args.code
        )
        result = transfer_resource(resource)
        
        if result.success:
            print(f"\n✅ 转存成功!")
            if result.share_link:
                print(f"   分享链接: {result.share_link}")
            if result.extract_code:
                print(f"   提取码: {result.extract_code}")
        else:
            print(f"\n❌ 转存失败: {result.error}")
        return
    
    # 批量转存
    if args.batch:
        try:
            with open(args.batch, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            resources = []
            for item in data.get('resources', []):
                resources.append(Resource(
                    title=item.get('title', '未命名'),
                    pan_type=item.get('pan_type', '夸克'),
                    pan_link=item.get('pan_link', ''),
                    extract_code=item.get('extract_code')
                ))
            
            results = batch_transfer(resources, args.delay)
            
            # 保存结果
            output_file = f"transfer_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'total': len(results),
                    'success': sum(1 for r in results if r.success),
                    'failed': sum(1 for r in results if not r.success),
                    'results': [
                        {
                            'original_link': r.original_link,
                            'share_link': r.share_link,
                            'extract_code': r.extract_code,
                            'success': r.success,
                            'error': r.error,
                            'duration': r.duration
                        } for r in results
                    ]
                }, f, ensure_ascii=False, indent=2)
            print(f"\n📁 结果已保存: {output_file}")
            
        except Exception as e:
            print(f"❌ 批量转存失败: {e}")
        return
    
    parser.print_help()


if __name__ == '__main__':
    main()
