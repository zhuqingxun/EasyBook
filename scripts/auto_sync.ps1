# EasyBook Meilisearch 自动同步脚本
# 开机静默执行：启动 Docker → 启动容器 → 运行 sync_meilisearch
# 同步完成后创建标记文件，后续开机不再执行

$ErrorActionPreference = "Continue"

$PROJECT_ROOT = "D:\CODE\EasyBook"
$BACKEND_DIR = "$PROJECT_ROOT\backend"
$LOG_FILE = "$PROJECT_ROOT\scripts\auto_sync.log"
$MARKER_FILE = "$BACKEND_DIR\data\sync_completed.marker"
$MUTEX_NAME = "Global\EasyBookAutoSync"

# ── 日志函数 ──
function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "$timestamp [$Level] $Message"
    Add-Content -Path $LOG_FILE -Value $line -Encoding UTF8
}

# ── 互斥锁：防止重复运行 ──
$mutex = $null
try {
    $mutex = [System.Threading.Mutex]::OpenExisting($MUTEX_NAME)
    Write-Log "检测到另一个实例正在运行，退出" "WARN"
    exit 0
} catch {
    $mutex = New-Object System.Threading.Mutex($true, $MUTEX_NAME)
}

try {
    Write-Log "========== 自动同步启动 =========="

    # ── 检查完成标记 ──
    if (Test-Path $MARKER_FILE) {
        Write-Log "同步已完成（标记文件存在），跳过"
        exit 0
    }

    # ── 启动 Docker Desktop ──
    $dockerProcess = Get-Process "Docker Desktop" -ErrorAction SilentlyContinue
    if (-not $dockerProcess) {
        Write-Log "Docker Desktop 未运行，正在启动..."
        Start-Process -FilePath "C:\Program Files\Docker\Docker\Docker Desktop.exe" -WindowStyle Hidden
        Write-Log "已发送 Docker Desktop 启动命令"
    } else {
        Write-Log "Docker Desktop 已在运行"
    }

    # ── 等待 Docker daemon 就绪 ──
    Write-Log "等待 Docker daemon 就绪..."
    $maxWait = 180  # 最多等 3 分钟
    $waited = 0
    while ($waited -lt $maxWait) {
        $null = & docker info 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Log "Docker daemon 已就绪（等待 ${waited}s）"
            break
        }
        Start-Sleep -Seconds 5
        $waited += 5
    }
    if ($waited -ge $maxWait) {
        Write-Log "Docker daemon 启动超时（${maxWait}s），退出" "ERROR"
        exit 1
    }

    # ── 启动 PostgreSQL + Meilisearch 容器 ──
    Write-Log "启动 EasyBook 容器..."
    Set-Location $PROJECT_ROOT
    $composeOutput = & docker-compose up -d postgres meilisearch 2>&1
    $composeOutput | ForEach-Object { Write-Log "$_" }
    Write-Log "docker-compose 完成（exitcode=$LASTEXITCODE）"

    # ── 等待容器健康 ──
    Write-Log "等待容器健康检查..."
    $maxWait = 120
    $waited = 0
    while ($waited -lt $maxWait) {
        $pgHealth = (& docker inspect --format="{{.State.Health.Status}}" easybook-postgres 2>&1) | Select-Object -Last 1
        $msHealth = (& docker inspect --format="{{.State.Health.Status}}" easybook-meilisearch 2>&1) | Select-Object -Last 1
        if ("$pgHealth" -eq "healthy" -and "$msHealth" -eq "healthy") {
            Write-Log "所有容器健康就绪（等待 ${waited}s）"
            break
        }
        Write-Log "容器状态: PG=$pgHealth, MS=$msHealth，继续等待..."
        Start-Sleep -Seconds 10
        $waited += 10
    }
    if ($waited -ge $maxWait) {
        Write-Log "容器健康检查超时，退出" "ERROR"
        exit 1
    }

    # ── 运行 Meilisearch 同步 ──
    Write-Log "开始 Meilisearch 同步..."
    Set-Location $BACKEND_DIR

    $syncProcess = Start-Process -FilePath "uv" `
        -ArgumentList "run", "python", "-m", "etl.sync_meilisearch" `
        -WorkingDirectory $BACKEND_DIR `
        -WindowStyle Hidden `
        -RedirectStandardOutput "$PROJECT_ROOT\scripts\sync_stdout.log" `
        -RedirectStandardError "$PROJECT_ROOT\scripts\sync_stderr.log" `
        -PassThru `
        -Wait

    $exitCode = $syncProcess.ExitCode
    Write-Log "同步脚本退出码: $exitCode"

    if ($exitCode -eq 0) {
        # 创建完成标记
        New-Item -Path $MARKER_FILE -ItemType File -Force | Out-Null
        Set-Content -Path $MARKER_FILE -Value "Completed at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -Encoding UTF8
        Write-Log "同步成功完成，已创建标记文件"
    } else {
        Write-Log "同步脚本异常退出（code=$exitCode），下次开机将重试" "ERROR"
    }

    Write-Log "========== 自动同步结束 =========="

} catch {
    Write-Log "未捕获异常: $($_.Exception.Message)" "ERROR"
} finally {
    if ($mutex) {
        $mutex.ReleaseMutex()
        $mutex.Dispose()
    }
}
