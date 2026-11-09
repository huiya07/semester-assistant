# 一键安装并启动（国内网络加速版）
#
# 用法：右键「使用 PowerShell 运行」，或在终端里执行：
#     pwsh -File .\setup.ps1
#
# 说明：默认从华为云镜像拉取 Python 依赖、从 npmmirror 拉取前端依赖；
#       嵌入模型已在代码里默认走 hf-mirror.com，无需额外配置。

$ErrorActionPreference = "Stop"
$mirror = "https://repo.huaweicloud.com/repository/pypi/simple"
$npmMirror = "https://registry.npmmirror.com"

Write-Host "[1/3] 安装后端依赖（约 1GB，首次较慢）…" -ForegroundColor Cyan
uv sync --default-index $mirror

Write-Host "[2/3] 构建前端…" -ForegroundColor Cyan
Push-Location frontend
try {
    if (-not (Test-Path node_modules)) {
        Write-Host "      首次需要安装前端依赖…" -ForegroundColor DarkGray
        npm install --registry=$npmMirror
    }
    npm run build
}
finally {
    Pop-Location
}

Write-Host "[3/3] 启动服务…" -ForegroundColor Cyan
Write-Host "      浏览器打开 http://127.0.0.1:8000" -ForegroundColor DarkGray
uv run uvicorn backend.app.main:app --port 8000
