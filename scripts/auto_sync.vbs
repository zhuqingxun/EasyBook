' EasyBook 静默启动包装器
' 通过 wscript.exe 调用，实现完全无窗口运行

Set WshShell = CreateObject("WScript.Shell")

' 先清理可能的残留进程
WshShell.Run "cmd /c taskkill /F /IM powershell.exe /FI ""WINDOWTITLE eq EasyBookSync"" >nul 2>&1", 0, True

' 静默运行 PowerShell 脚本（0 = 隐藏窗口，True = 等待完成）
WshShell.Run "powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -File ""D:\CODE\EasyBook\scripts\auto_sync.ps1""", 0, True

Set WshShell = Nothing
