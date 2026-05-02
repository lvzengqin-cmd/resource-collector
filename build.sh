#!/bin/bash
# Netlify 构建脚本

echo "开始构建..."
echo "仓库: resource-collector"
echo "时间: $(date)"

# 采集资源（可选）
if [ "$RUN_COLLECTION" = "true" ]; then
    echo "运行资源采集..."
    pip install requests
    python collector.py
fi

# 部署已完成（静态文件在 dist 目录）
echo "部署静态文件..."
echo "构建完成!"
