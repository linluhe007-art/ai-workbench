# Phase 2.5 验证脚本
$ErrorActionPreference = "Continue"
Set-Location "E:\半自动工作台"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Phase 2.5 架构稳定优化 — 验证" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. 重启后端 (加载新依赖)
Write-Host "[1/5] 重建后端容器 (安装 pytest) ..." -ForegroundColor Yellow
docker compose up --build -d backend 2>&1
Start-Sleep -Seconds 10

# 2. 健康检查
Write-Host ""
Write-Host "[2/5] 健康检查 ..." -ForegroundColor Yellow
try {
    $h = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/health" -TimeoutSec 10
    Write-Host "  Backend: OK" -ForegroundColor Green
} catch {
    Write-Host "  Backend: FAILED" -ForegroundColor Red
    docker compose logs backend --tail=20
    exit 1
}

# 3. 测试 Memory 索引
Write-Host ""
Write-Host "[3/5] 测试 Memory 索引 ..." -ForegroundColor Yellow
try {
    # 刷新索引
    $refresh = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/memory/refresh?full=true" -Method POST -TimeoutSec 30
    Write-Host "  索引刷新: $($refresh.files_updated) 文件更新" -ForegroundColor Green

    # 统计
    $stats = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/memory/stats" -TimeoutSec 10
    Write-Host "  索引文件数: $($stats.data.total_indexed)" -ForegroundColor Green

    # 搜索测试
    $search = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/memory/search" -Method POST -ContentType "application/json" -Body '{"keyword": "AI漫剧", "limit": 5}' -TimeoutSec 10
    Write-Host "  搜索 'AI漫剧': $($search.total) 条结果" -ForegroundColor Green
    if ($search.results.Count -gt 0) {
        Write-Host "    Top: $($search.results[0].title) (score: $($search.results[0].relevance))" -ForegroundColor Gray
    }
} catch {
    Write-Host "  Memory 测试失败: $($_.Exception.Message)" -ForegroundColor Red
}

# 4. 测试 Orchestrator
Write-Host ""
Write-Host "[4/5] 测试 Orchestrator ..." -ForegroundColor Yellow
try {
    $result = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/orchestrator/run" -Method POST -ContentType "application/json" -Body '{"task": "根据我的知识库写一个AI漫剧方案"}' -TimeoutSec 30
    Write-Host "  状态: $($result.status)" -ForegroundColor Green
    Write-Host "  耗时: $($result.total_duration_ms)ms" -ForegroundColor Green
    if ($result.memory_context) {
        Write-Host "  Memory 文档数: $($result.memory_context.documents_count)" -ForegroundColor Green
        Write-Host "  Memory 标签: $($result.memory_context.tags -join ', ')" -ForegroundColor Gray
    }
    foreach ($s in $result.steps_summary) {
        $color = if ($s.status -eq "success") { "Green" } else { "Yellow" }
        Write-Host "    - [$($s.step_id)] $($s.status)" -ForegroundColor $color
    }
} catch {
    Write-Host "  Orchestrator 测试失败: $($_.Exception.Message)" -ForegroundColor Red
}

# 5. 测试 Agent 列表
Write-Host ""
Write-Host "[5/5] 测试 Agent 列表 ..." -ForegroundColor Yellow
try {
    $agents = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/orchestrator/agents" -TimeoutSec 10
    Write-Host "  已注册 Agent: $($agents.agents.Count)" -ForegroundColor Green
} catch {
    Write-Host "  Agent 列表失败: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  验证完成" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan