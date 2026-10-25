# 一键安装并启动（国内网络加速版）
#
# 用法：右键「使用 PowerShell 运行」，或在终端里执行：
#     pwsh -File .\setup.ps1
#
# 说明：默认从华为云镜像拉取依赖（实测比官方源快一个数量级）；
#       嵌入模型已在代码里默认走 hf-mirror.com，无需额外配置。
# 想用官方源：删掉下面的 --default-index 参数即可。

$ErrorActionPreference = "Stop"
$mirror = "https://repo.huaweicloud.com/repository/pypi/simple"

Write-Host "[1/2] 安装依赖（约 1GB，首次较慢）…" -ForegroundColor Cyan
uv sync --default-index $mirror

Write-Host "[2/2] 启动界面…" -ForegroundColor Cyan
Write-Host "      浏览器打开 http://127.0.0.1:8501" -ForegroundColor DarkGray
uv run streamlit run app.py
