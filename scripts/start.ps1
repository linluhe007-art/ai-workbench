# AI Workbench - 启动 & 诊断脚本
# 在 PowerShell 中运行（你的用户账户，非沙箱）

$ErrorActionPreference = "Continue"
Set-Location "E:\半自动工作台"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  AI Workbench - Docker 启动脚本" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: 检查 Docker
Write-Host "[1/5] 检查 Docker ..." -ForegroundColor Yellow
try {
    $dv = docker --version 2>&1
    Write-Host "  Docker: $dv" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: docker 命令不可用，请启动 Docker Desktop" -ForegroundColor Red
    exit 1
}

try {
    $cv = docker compose version 2>&1
    Write-Host "  Compose: $cv" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: docker compose 不可用" -ForegroundColor Red
    exit 1
}

# Step 2: 检查端口占用
Write-Host ""
Write-Host "[2/5] 检查端口 ..." -ForegroundColor Yellow
$ports = @(5173, 8000, 5432, 6379)
foreach ($p in $ports) {
    $conn = Get-NetTCPConnection -LocalPort $p -ErrorAction SilentlyContinue
    if ($conn) {
        Write-Host "  Port $p : OCCUPIED (PID $($conn[0].OwningProcess))" -ForegroundColor Red
    } else {
        Write-Host "  Port $p : free" -ForegroundColor Green
    }
}

# Step 3: 停止旧容器
Write-Host ""
Write-Host "[3/5] 清理旧容器 ..." -ForegroundColor Yellow
docker compose down 2>&1 | Out-Null
Write-Host "  Done" -ForegroundColor Green

# Step 4: 构建并启动
Write-Host ""
Write-Host "[4/5] 构建并启动容器 (可能需要几分钟) ..." -ForegroundColor Yellow
docker compose up --build -d 2>&1

# Step 5: 等待并检查
Write-Host ""
Write-Host "[5/5] 等待服务就绪 (20秒) ..." -ForegroundColor Yellow
Start-Sleep -Seconds 20

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  服务状态" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
docker compose ps

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  健康检查" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Backend health
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/health" -TimeoutSec 5
    Write-Host "  Backend:  OK ($($health | ConvertTo-Json -Compress))" -ForegroundColor Green
} catch {
    Write-Host "  Backend:  FAILED - $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "--- Backend Logs ---" -ForegroundColor Red
    docker compose logs backend --tail=30
}

# DB health
try {
    $dbHealth = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/health/db" -TimeoutSec 5
    Write-Host "  Database: $($dbHealth.status)" -ForegroundColor $(if($dbHealth.status -eq "healthy"){"Green"}else{"Red"})
} catch {
    Write-Host "  Database: FAILED" -ForegroundColor Red
}

# Redis health
try {
    $redisHealth = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/health/redis" -TimeoutSec 5
    Write-Host "  Redis:    $($redisHealth.status)" -ForegroundColor $(if($redisHealth.status -eq "healthy"){"Green"}else{"Red"})
} catch {
    Write-Host "  Redis:    FAILED" -ForegroundColor Red
}

# Frontend
try {
    $feResp = Invoke-WebRequest -Uri "http://localhost:5173" -TimeoutSec 5 -UseBasicParsing
    Write-Host "  Frontend: OK (HTTP $($feResp.StatusCode))" -ForegroundColor Green
} catch {
    Write-Host "  Frontend: FAILED - $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "--- Frontend Logs ---" -ForegroundColor Red
    docker compose logs frontend --tail=30
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  访问地址" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  前端:     http://localhost:5173"
Write-Host "  API 文档: http://localhost:8000/docs"
Write-Host "  健康检查: http://localhost:8000/api/v1/health/all"
Write-Host ""
Write-Host "查看全部日志: docker compose logs -f" -ForegroundColor Gray
Write-Host "停止服务:     docker compose down" -ForegroundColor Gray