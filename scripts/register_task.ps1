# 注册 EasyBook 自动同步计划任务
# 需要管理员权限运行

$TaskName = "EasyBookAutoSync"
$VbsPath = "D:\CODE\EasyBook\scripts\auto_sync.vbs"

# 检查任务是否已存在
$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "计划任务 '$TaskName' 已存在，正在更新..."
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# 触发器：用户登录时
$trigger = New-ScheduledTaskTrigger -AtLogOn

# 操作：wscript.exe 运行 VBS
$action = New-ScheduledTaskAction -Execute "wscript.exe" -Argument "`"$VbsPath`""

# 设置：允许按需运行，不限制运行时长
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 24)

# 注册任务
Register-ScheduledTask `
    -TaskName $TaskName `
    -Trigger $trigger `
    -Action $action `
    -Settings $settings `
    -Description "EasyBook: 开机自动同步 Meilisearch（一次性，完成后不再执行）" `
    -RunLevel Limited

Write-Host ""
Write-Host "计划任务 '$TaskName' 注册成功！"
Write-Host "  触发: 用户登录时"
Write-Host "  操作: wscript.exe -> auto_sync.vbs -> auto_sync.ps1"
Write-Host "  时限: 24 小时"
Write-Host ""
Write-Host "手动测试: schtasks /run /tn $TaskName"
Write-Host "查看状态: schtasks /query /tn $TaskName /v"
Write-Host "删除任务: schtasks /delete /tn $TaskName /f"
