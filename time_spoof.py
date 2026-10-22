import argparse
import ctypes
import datetime
import os
import platform
import subprocess
import sys
import time


def is_admin():
  """检查管理员/Root权限"""
  if platform.system() == "Windows":
    return ctypes.windll.shell32.IsUserAnAdmin() != 0
  return os.geteuid() == 0


def toggle_ntp(enable: bool):
  """开关系统自动时间同步服务"""
  sys_type = platform.system()
  if sys_type == "Windows":
    cmd = (
        "net start w32time && w32tm /resync" if enable else "net stop w32time"
    )
  elif sys_type == "Linux":
    state = "true" if enable else "false"
    cmd = f"timedatectl set-ntp {state}"
  elif sys_type == "Darwin":
    state = "on" if enable else "off"
    cmd = f"systemsetup -setusingnetworktime {state}"
  else:
    return
  subprocess.run(
      cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
  )


def set_sys_time(dt: datetime.datetime):
  """跨平台修改系统时间"""
  sys_type = platform.system()
  if sys_type == "Windows":
    subprocess.run(f"date {dt.strftime('%Y-%m-%d')}", shell=True, check=True)
    subprocess.run(f"time {dt.strftime('%H:%M:%S')}", shell=True, check=True)
  elif sys_type == "Linux":
    subprocess.run(
        f'date -s "{dt.strftime("%Y-%m-%d %H:%M:%S")}"', shell=True, check=True
    )
  elif sys_type == "Darwin":
    subprocess.run(
        f"date {dt.strftime('%m%d%H%M%Y.%S')}", shell=True, check=True
    )


def main():
  parser = argparse.ArgumentParser(
      description="跨平台背景时间修改与自动矫正执行器"
  )
  parser.add_argument(
      "-t",
      "--time",
      required=True,
      help="目标背景时间，格式: 'YYYY-MM-DD HH:MM:SS'",
  )
  parser.add_argument(
      "-c",
      "--cmd",
      required=True,
      help="在此时间下要执行的脚本或命令，例如: 'python test.py'",
  )
  args = parser.parse_args()

  if not is_admin():
    print("❌ 权限不足：请使用管理员身份 (Windows) 或 sudo (Linux/macOS) 运行！")
    sys.exit(1)

  real_start = datetime.datetime.now()
  mono_start = time.monotonic()
  target_dt = datetime.datetime.strptime(args.time, "%Y-%m-%d %H:%M:%S")

  try:
    print(f"🔒 正在锁定背景时间为: {target_dt}")
    toggle_ntp(False)
    set_sys_time(target_dt)

    print(f"🚀 开始执行命令: {args.cmd}\n" + "-" * 40)
    subprocess.run(args.cmd, shell=True)
    print("-" * 40)

  finally:
    elapsed = time.monotonic() - mono_start
    corrected_time = real_start + datetime.timedelta(seconds=elapsed)
    print(
        f"⏱️ 执行耗时 {elapsed:.2f} 秒，正在矫正系统时间为:"
        f" {corrected_time.strftime('%Y-%m-%d %H:%M:%S')}"
    )
    set_sys_time(corrected_time)
    toggle_ntp(True)
    print("✅ 时间已完整恢复！")


if __name__ == "__main__":
  main()
