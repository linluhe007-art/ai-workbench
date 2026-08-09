# Phase 2.6 验证脚本
$ErrorActionPreference = "Continue"
Set-Location "E:\半自动工作台"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Phase 2.6 架构稳定优化 — 验证" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. 重建后端
Write-Host "[1/5] 重建后端容器 ..." -ForegroundColor Yellow
docker compose up --build -d backend 2>&1
Start-Sleep -Seconds 15

# 2. 健康检查
Write-Host ""
Write-Host "[2/5] 健康检查 ..." -ForegroundColor Yellow
try {
    $h = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/health" -TimeoutSec 10
    Write-Host "  Backend: OK" -ForegroundColor Green
} catch {
    Write-Host "  Backend: FAILED" -ForegroundColor Red
    docker compose logs backend --tail=30
    exit 1
}

# 3. Memory 索引测试
Write-Host ""
Write-Host "[3/5] Memory 索引测试 ..." -ForegroundColor Yellow
try {
    $refresh = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/memory/refresh?full=true" -Method POST -TimeoutSec 30
    Write-Host "  索引刷新: $($refresh.files_updated) 文件" -ForegroundColor Green

    $stats = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/memory/stats" -TimeoutSec 10
    Write-Host "  索引总数: $($stats.data.total_indexed)" -ForegroundColor Green
    Write-Host "  Schema版本: $($stats.data.schema_version)" -ForegroundColor Green

    $search = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/memory/search" -Method POST -ContentType "application/json" -Body '{"keyword": "AI漫剧", "limit": 5}' -TimeoutSec 10
    Write-Host "  搜索 'AI漫剧': $($search.total) 条" -ForegroundColor Green
} catch {
    Write-Host "  Memory 测试失败: $($_.Exception.Message)" -ForegroundColor Red
}

# 4. Orchestrator 测试
Write-Host ""
Write-Host "[4/5] Orchestrator 测试 ..." -ForegroundColor Yellow
try {
    $result = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/orchestrator/run" -Method POST -ContentType "application/json" -Body '{"task": "根据我的知识库写一个AI漫剧方案"}' -TimeoutSec 30
    Write-Host "  task_id: $($result.task_id)" -ForegroundColor Green
    Write-Host "  状态: $($result.status)" -ForegroundColor Green
    Write-Host "  created_at: $($result.created_at)" -ForegroundColor Gray

    # 查询任务状态
    $task = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/orchestrator/tasks/$($result.task_id)" -TimeoutSec 10
    Write-Host "  任务状态查询: $($task.status)" -ForegroundColor Green
} catch {
    Write-Host "  Orchestrator 测试失败: $($_.Exception.Message)" -ForegroundColor Red
}

# 5. Agent 列表
Write-Host ""
Write-Host "[5/5] Agent 列表 ..." -ForegroundColor Yellow
try {
    $agents = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/orchestrator/agents" -TimeoutSec 10
    Write-Host "  已注册 Agent: $($agents.agents.Count)" -ForegroundColor Green
} catch {
    Write-Host "  失败: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  验证完成" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan