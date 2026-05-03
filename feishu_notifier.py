"""
飞书Webhook告警模块
用于采集任务完成/失败时发送通知
"""

import json
import requests
from datetime import datetime
from typing import Optional, Dict, Any


class FeishuNotifier:
    """飞书机器人通知器"""
    
    def __init__(self, webhook_url: str = None):
        """
        初始化飞书通知器
        
        Args:
            webhook_url: 飞书机器人的Webhook地址
        """
        self.webhook_url = webhook_url
        
    def send(self, title: str, content: str, msg_type: str = "text") -> bool:
        """
        发送消息到飞书
        
        Args:
            title: 消息标题
            content: 消息内容
            msg_type: 消息类型 (text/post)
            
        Returns:
            bool: 发送是否成功
        """
        if not self.webhook_url:
            print("⚠️ 飞书Webhook未配置，跳过通知")
            return False
            
        try:
            # 构建富文本消息
            payload = {
                "msg_type": "post",
                "content": {
                    "post": {
                        "zh_cn": {
                            "title": title,
                            "content": [
                                [
                                    {
                                        "tag": "text",
                                        "text": content
                                    }
                                ]
                            ]
                        }
                    }
                }
            }
            
            response = requests.post(
                self.webhook_url,
                headers={"Content-Type": "application/json"},
                data=json.dumps(payload),
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("code") == 0:
                    print(f"✅ 飞书通知发送成功")
                    return True
                else:
                    print(f"❌ 飞书通知失败: {result.get('msg')}")
                    return False
            else:
                print(f"❌ 飞书通知HTTP错误: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ 飞书通知异常: {str(e)}")
            return False
    
    def send_success(self, summary: Dict[str, Any]) -> bool:
        """发送采集成功通知"""
        title = "✅ 资源采集任务完成"
        
        total = summary.get("total", 0)
        new_count = summary.get("new_count", 0)
        duration = summary.get("duration", 0)
        sources_count = summary.get("sources_count", 0)
        
        content = f"""📊 采集统计
━━━━━━━━━━━━━━━
• 采集源数量: {sources_count}
• 处理链接数: {total}
• 新增入库: {new_count}
• 耗时: {duration:.1f}秒
• 时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}

🌐 访问CY资源宝库: https://www.cybaoku.com"""
        
        return self.send(title, content)
    
    def send_failure(self, error_msg: str, duration: float = 0) -> bool:
        """发送采集失败通知"""
        title = "❌ 资源采集任务失败"
        
        content = f"""⚠️ 采集异常
━━━━━━━━━━━━━━━
• 错误信息: {error_msg}
• 耗时: {duration:.1f}秒
• 时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}

🔧 请检查GitHub Actions日志"""

        return self.send(title, content)


# 全局通知器实例
_feishu_notifier: Optional[FeishuNotifier] = None


def init_notifier(webhook_url: str = None) -> FeishuNotifier:
    """初始化通知器"""
    global _feishu_notifier
    _feishu_notifier = FeishuNotifier(webhook_url)
    return _feishu_notifier


def get_notifier() -> Optional[FeishuNotifier]:
    """获取通知器实例"""
    return _feishu_notifier


def notify_success(summary: Dict[str, Any]) -> bool:
    """快捷函数：发送成功通知"""
    notifier = get_notifier()
    if notifier:
        return notifier.send_success(summary)
    return False


def notify_failure(error_msg: str, duration: float = 0) -> bool:
    """快捷函数：发送失败通知"""
    notifier = get_notifier()
    if notifier:
        return notifier.send_failure(error_msg, duration)
    return False
