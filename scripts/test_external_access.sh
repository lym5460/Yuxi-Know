#!/bin/bash

echo "=== 外网访问诊断脚本 ==="
echo ""

echo "1. 检查服务监听状态:"
ss -tlnp | grep :80
echo ""

echo "2. 检查本地访问:"
curl -I http://localhost:80/ 2>&1 | head -5
echo ""

echo "3. 检查内网 IP 访问:"
curl -I http://192.168.1.101:80/ 2>&1 | head -5
echo ""

echo "4. 检查 Docker 容器状态:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "web-prod|api-prod"
echo ""

echo "5. 检查 Nginx 日志 (最后 10 行):"
docker logs web-prod --tail 10 2>&1
echo ""

echo "=== 诊断完成 ==="
echo ""
echo "如果本地和内网访问都正常,但外网不行,请检查:"
echo "1. 路由器端口映射: 外网端口 -> 192.168.1.101:80"
echo "2. 云服务商安全组: 开放对应的外网端口"
echo "3. 系统防火墙: sudo ufw status"
