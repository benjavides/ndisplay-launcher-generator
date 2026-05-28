from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import subprocess


@dataclass(frozen=True)
class LaunchProfile:
    unreal_editor_path: str
    uproject_path: str
    ndisplay_path: str
    map_path: str
    node_name: str = "Node_0"
    stage_name: str = "Node_0"


def _ps_single_quoted(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def write_launch_profile(profile: LaunchProfile, output_dir: Path, profile_name: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    profile_path = output_dir / f"{profile_name}.ndisplay-launch.json"
    log_path = str(profile_path.with_suffix("")) + ".launcher.log"
    payload = {
        **profile.__dict__,
        "launch_args": build_unreal_args(profile),
        "log_path": log_path,
        "launcher_script": _build_launcher_script_body(),
    }
    profile_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return profile_path


def create_windows_shortcut(
    shortcut_path: Path,
    profile_path: Path,
    icon_path: Path | None = None,
) -> None:
    shortcut_path.parent.mkdir(parents=True, exist_ok=True)
    target = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
    profile_str = str(profile_path).replace("'", "''")
    bootstrap = (
        f"$j = Get-Content -Raw -LiteralPath '{profile_str}' | ConvertFrom-Json; "
        "Invoke-Expression $j.launcher_script"
    )
    args = (
        f'-NoProfile -NoExit -ExecutionPolicy Bypass -WindowStyle Normal -Command "{bootstrap}"'
    )
    working_dir = str(profile_path.parent)
    icon = str(icon_path) if icon_path else str(target)

    ps_script = (
        "$shell = New-Object -ComObject WScript.Shell\n"
        f"$shortcut = $shell.CreateShortcut({_ps_single_quoted(str(shortcut_path))})\n"
        f"$shortcut.TargetPath = {_ps_single_quoted(target)}\n"
        f"$shortcut.Arguments = {_ps_single_quoted(args)}\n"
        f"$shortcut.WorkingDirectory = {_ps_single_quoted(working_dir)}\n"
        f"$shortcut.IconLocation = {_ps_single_quoted(icon)}\n"
        "$shortcut.Save()\n"
    )

    completed = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip() or "Unknown error creating shortcut."
        raise RuntimeError(stderr)


def _build_launcher_script_body() -> str:
    lines = [
        '$ErrorActionPreference = "Stop"',
        '$logPath = $j.log_path',
        '',
        'function Write-LauncherLog { param([string]$Message)',
        '    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"',
        '    $line = "[$stamp] $Message"',
        '    Add-Content -Path $logPath -Value $line',
        '    Write-Host $line',
        '}',
        '',
        '# Job Object ensures child processes are killed when this window closes',
        'Add-Type -TypeDefinition @"',
        'using System;',
        'using System.Runtime.InteropServices;',
        'public static class JobObject {',
        '    [DllImport("kernel32.dll", CharSet = CharSet.Unicode)]',
        '    public static extern IntPtr CreateJobObject(IntPtr lpJobAttributes, string lpName);',
        '    [DllImport("kernel32.dll")]',
        '    public static extern bool SetInformationJobObject(IntPtr hJob, int JobObjectInfoClass, IntPtr lpJobObjectInfo, uint cbJobObjectInfoLength);',
        '    [DllImport("kernel32.dll", SetLastError = true)]',
        '    public static extern bool AssignProcessToJobObject(IntPtr hJob, IntPtr hProcess);',
        '    [StructLayout(LayoutKind.Sequential)]',
        '    public struct JOBOBJECT_BASIC_LIMIT_INFORMATION {',
        '        public long PerProcessUserTimeLimit;',
        '        public long PerJobUserTimeLimit;',
        '        public uint LimitFlags;',
        '        public UIntPtr MinimumWorkingSetSize;',
        '        public UIntPtr MaximumWorkingSetSize;',
        '        public uint ActiveProcessLimit;',
        '        public IntPtr Affinity;',
        '        public uint PriorityClass;',
        '        public uint SchedulingClass;',
        '    }',
        '    [StructLayout(LayoutKind.Sequential)]',
        '    public struct IO_COUNTERS {',
        '        public ulong ReadOperationCount;',
        '        public ulong WriteOperationCount;',
        '        public ulong OtherOperationCount;',
        '        public ulong ReadTransferCount;',
        '        public ulong WriteTransferCount;',
        '        public ulong OtherTransferCount;',
        '    }',
        '    [StructLayout(LayoutKind.Sequential)]',
        '    public struct JOBOBJECT_EXTENDED_LIMIT_INFORMATION {',
        '        public JOBOBJECT_BASIC_LIMIT_INFORMATION BasicLimitInformation;',
        '        public IO_COUNTERS IoInfo;',
        '        public UIntPtr ProcessMemoryLimit;',
        '        public UIntPtr JobMemoryLimit;',
        '        public UIntPtr PeakProcessMemoryUsed;',
        '        public UIntPtr PeakJobMemoryUsed;',
        '    }',
        '    public const int JobObjectExtendedLimitInformation = 9;',
        '    public const uint JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000;',
        '    public static IntPtr CreateKillOnCloseJob() {',
        '        IntPtr job = CreateJobObject(IntPtr.Zero, null);',
        '        JOBOBJECT_EXTENDED_LIMIT_INFORMATION info = new JOBOBJECT_EXTENDED_LIMIT_INFORMATION();',
        '        info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;',
        '        int length = Marshal.SizeOf(typeof(JOBOBJECT_EXTENDED_LIMIT_INFORMATION));',
        '        IntPtr infoPtr = Marshal.AllocHGlobal(length);',
        '        try {',
        '            Marshal.StructureToPtr(info, infoPtr, false);',
        '            SetInformationJobObject(job, JobObjectExtendedLimitInformation, infoPtr, (uint)length);',
        '        } finally {',
        '            Marshal.FreeHGlobal(infoPtr);',
        '        }',
        '        return job;',
        '    }',
        '}',
        '"@',
        '',
        'try {',
        '    $editor = $j.unreal_editor_path',
        '    $uproject = $j.uproject_path',
        '    $ndisplay = $j.ndisplay_path',
        '    $launchArgs = $j.launch_args',
        '    if (-not (Test-Path $editor)) { throw "UnrealEditor.exe not found: $editor" }',
        '    if (-not (Test-Path $uproject)) { throw "Project file not found: $uproject" }',
        '    if (-not (Test-Path $ndisplay)) { throw "nDisplay config not found: $ndisplay" }',
        '',
        '    $jobHandle = [JobObject]::CreateKillOnCloseJob()',
        '    Write-LauncherLog "Launching $editor"',
        '    $proc = Start-Process -FilePath $editor -ArgumentList $launchArgs -PassThru',
        '    [JobObject]::AssignProcessToJobObject($jobHandle, $proc.Handle) | Out-Null',
        '    Write-LauncherLog "Launched Unreal. PID: $($proc.Id)"',
        '',
        '    Write-Host ""',
        '    Write-Host "========================================" -ForegroundColor Cyan',
        '    Write-Host "  CLOSE THIS WINDOW TO STOP UNREAL" -ForegroundColor Yellow',
        '    Write-Host "========================================" -ForegroundColor Cyan',
        '    Write-Host ""',
        '    Write-Host "Unreal is running. Closing this window will terminate the editor."',
        '    Write-Host ""',
        '',
        '    # Wait for Unreal to exit (or window to be closed)',
        '    $proc.WaitForExit()',
        '    Write-LauncherLog "Unreal exited with code: $($proc.ExitCode)"',
        '}',
        'catch {',
        '    Write-LauncherLog "ERROR: $($_.Exception.Message)"',
        '    Write-Host "Launch failed. See log: $logPath" -ForegroundColor Red',
        '    Write-Host ""',
        '    Write-Host "Press ENTER to close this window..."',
        '    [void][Console]::ReadLine()',
        '}',
    ]
    return "\n".join(lines) + "\n"


def build_unreal_args(profile: LaunchProfile) -> list[str]:
    return [
        profile.uproject_path,
        profile.map_path,
        "-game",
        "None",
        "-messaging",
        "-dc_cluster",
        "-nosplash",
        "-fixedseed",
        "-NoVerifyGC",
        "-noxrstereo",
        "-xrtrackingonly",
        "-RemoteControlIsHeadless",
        f'-StageFriendlyName="{profile.stage_name}"',
        "-MaxGPUCount=2",
        f'-dc_cfg="{profile.ndisplay_path}"',
        "-dx12",
        "-dc_dev_mono",
        "-nosound",
        "-NoLoadingScreen",
        "-DisablePython",
        f"-dc_node={profile.node_name}",
        f"Log={profile.node_name}.log",
        "-ini:Engine:[/Script/Engine.Engine]:GameEngine=/Script/DisplayCluster.DisplayClusterGameEngine,[/Script/Engine.Engine]:GameViewportClientClassName=/Script/DisplayCluster.DisplayClusterViewportClient,[/Script/Engine.UserInterfaceSettings]:bAllowHighDPIInGameMode=True",
        "-ini:Game:[/Script/EngineSettings.GeneralProjectSettings]:bUseBorderlessWindow=True",
        "-ini:Input:[/Script/Engine.InputSettings]:DefaultPlayerInputClass=/Script/DisplayCluster.DisplayClusterPlayerInput",
        "-unattended",
        "-NoScreenMessages",
        "-handleensurepercent=0",
        '-ExecCmds="DisableAllScreenMessages"',
        "-windowed",
        "-forceres",
        "WinX=0",
        "WinY=0",
        "ResX=5760",
        "ResY=1200",
        "-RenderOffscreen",
        f'-CONCERTDISPLAYNAME="{profile.node_name}"',
        "-CONCERTISHEADLESS",
        '-DPCVars="Slate.bAllowNotifications=0,p.Chaos.Solver.Deterministic=1,LevelInstance.ForceEditorWorldMode=1"',
    ]

