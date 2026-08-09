# Phase 2 验证脚本 — 测试 Orchestrator + Memory + Agent 端点
# 在 PowerShell 中运行

$ErrorActionPreference = "Continue"
Set-Location "E:\半自动工作台"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Phase 2 验证 — Orchestrator & Memory" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. 检查服务状态
Write-Host "[1/6] 检查 Docker 服务状态 ..." -ForegroundColor Yellow
docker compose ps
Write-Host ""

# 2. 健康检查
Write-Host "[2/6] 健康检查 ..." -ForegroundColor Yellow
try {
    $h = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/health/all" -TimeoutSec 5
    Write-Host "  状态: $($h.status)" -ForegroundColor Green
} catch {
    Write-Host "  后端未就绪，请先重启: docker compose up --build -d" -ForegroundColor Red
    exit 1
}
Write-Host ""

# 3. 测试 Orchestrator — 任务规划
Write-Host "[3/6] 测试任务规划 (POST /api/v1/orchestrator/plan) ..." -ForegroundColor Yellow
try {
    $plan = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/orchestrator/plan" `
        -Method POST -ContentType "application/json" `
        -Body '{"task": "写一篇关于AI最新进展的文章"}'
    Write-Host "  意图: $($plan.intent)" -ForegroundColor Green
    Write-Host "  步骤数: $($plan.steps.Count)" -ForegroundColor Green
    Write-Host "  查询: $($plan.context_query)" -ForegroundColor Green
    foreach ($s in $plan.steps) {
        Write-Host "    - [$($s.type)] $($s.description)" -ForegroundColor Gray
    }
} catch {
    Write-Host "  失败: $($_.Exception.Message)" -ForegroundColor Red
}
Write-Host ""

# 4. 测试 Orchestrator — 完整执行
Write-Host "[4/6] 测试任务执行 (POST /api/v1/orchestrator/run) ..." -ForegroundColor Yellow
try {
    $result = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/orchestrator/run" `
        -Method POST -ContentType "application/json" `
        -Body '{"task": "写一篇关于AI最新进展的文章"}'
    Write-Host "  状态: $($result.status)" -ForegroundColor Green
    Write-Host "  耗时: $($result.total_duration_ms)ms" -ForegroundColor Green
    Write-Host "  步骤结果:" -ForegroundColor Green
    foreach ($s in $result.steps_summary) {
        $color = if ($s.status -eq "success") { "Green" } else { "Red" }
        Write-Host "    - [$($s.step_id)] $($s.status) ($($s.agent))" -ForegroundColor $color
    }
} catch {
    Write-Host "  失败: $($_.Exception.Message)" -ForegroundColor Red
}
Write-Host ""

# 5. 测试 Agent 列表
Write-Host "[5/6] 测试 Agent 列表 (GET /api/v1/orchestrator/agents) ..." -ForegroundColor Yellow
try {
    $agents = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/orchestrator/agents" -TimeoutSec 5
    foreach ($a in $agents.agents) {
        Write-Host "  - $($a.name) [$($a.status)] caps: $($a.capabilities -join ', ')" -ForegroundColor Gray
    }
} catch {
    Write-Host "  失败: $($_.Exception.Message)" -ForegroundColor Red
}
Write-Host ""

# 6. 测试 Memory 端点
Write-Host "[6/6] 测试 Memory 端点 ..." -ForegroundColor Yellow
try {
    $stats = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/memory/stats" -TimeoutSec 5
    if ($stats.status -eq "ok") {
        Write-Host "  知识库路径: $($stats.data.vault_path)" -ForegroundColor Green
        Write-Host "  文件数: $($stats.data.total_files)" -ForegroundColor Green
        Write-Host "  文件夹数: $($stats.data.total_folders)" -ForegroundColor Green
    } else {
        Write-Host "  知识库未就绪: $($stats.message)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  失败: $($_.Exception.Message)" -ForegroundColor Red
}
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  验证完成" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "API 文档: http://localhost:8000/docs" -ForegroundColor Gray
Write-Host "新增端点:" -ForegroundColor Gray
Write-Host "  POST /api/v1/orchestrator/plan   — 任务规划" -ForegroundColor Gray
Write-Host "  POST /api/v1/orchestrator/run    — 任务执行" -ForegroundColor Gray
Write-Host "  GET  /api/v1/orchestrator/agents — Agent 列表" -ForegroundColor Gray
Write-Host "  GET  /api/v1/memory/stats        — 知识库统计" -ForegroundColor Gray
Write-Host "  GET  /api/v1/memory/files        — 文件列表" -ForegroundColor Gray
Write-Host "  POST /api/v1/memory/search       — 关键词搜索" -ForegroundColor Gray
Write-Host "  GET  /api/v1/memory/context      — 获取上下文" -ForegroundColor Gray