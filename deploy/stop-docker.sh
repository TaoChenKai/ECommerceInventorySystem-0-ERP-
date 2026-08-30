#!/usr/bin/env bash
# 电商库存管理系统 - 服务器 Docker 停止脚本
cd "$(dirname "$0")"
echo "正在停止 Docker 服务..."
docker compose down
echo "已停止。"
echo "如需同时删除数据库数据（不可恢复），请执行: docker compose down -v"
