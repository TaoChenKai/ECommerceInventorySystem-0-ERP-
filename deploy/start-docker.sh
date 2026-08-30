#!/usr/bin/env bash
# 电商库存管理系统 - 服务器 Docker 一键部署启动脚本
# 使用方式：在服务器上（已安装 Docker 与 Docker Compose）执行 bash start-docker.sh
set -e
cd "$(dirname "$0")"

echo "================================================"
echo "  电商库存管理系统 - Docker 一键部署启动"
echo "================================================"
echo

# 首次部署：从 .env.example 生成 .env（含数据库密码/密钥/老板账号）
if [ ! -f .env ]; then
    echo "[首次部署] 检测到 .env 不存在，正在从 .env.example 生成..."
    cp .env.example .env
    echo "[提示] 已生成 .env，其中含默认密码，生产环境请务必先编辑 .env 修改："
    echo "        POSTGRES_PASSWORD / SECRET_KEY / BOSS_PASSWORD"
    echo
    read -p "修改完成后按回车继续；不修改直接回车将使用默认配置..." -r
fi

# 构建镜像并后台启动
echo "[构建] 正在构建镜像并启动容器（首次构建需下载依赖，较慢）..."
docker compose up -d --build

echo
echo "================================================"
echo "  系统已启动！"
echo "   网页访问:  http://<服务器IP>       (或本机 http://localhost)"
echo "   后端文档:  http://<服务器IP>:8000/docs  (仅本机可见由防火墙控制)"
echo "   查看状态:  docker compose ps"
echo "   查看日志:  docker compose logs -f"
echo "================================================"
echo
docker compose ps
