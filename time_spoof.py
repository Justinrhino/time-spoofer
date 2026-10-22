#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import ctypes
import datetime
import os
import platform
import subprocess
import sys
import time


def is_admin():
  """检查当前是否拥有管理员 (Windows) 或 Root (Linux/macOS) 权限"""
  if platform.system() == "Windows":
    try:
      return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
      return False
  else:
    return os.geteuid() == 0


def toggle_ntp(enable: bool):
  """开关系统的自动网络时间同步服务，防止修改时间后被系统自动改回"""
  sys_type = platform.system()
  if sys_type == "Windows":
    cmd = (
        "net start w32time && w32tm /resync" if enable else "net stop w32time"
    )
  elif sys_type == "Linux":
    state = "true" if enable else "false"
    cmd = f"timedatectl set-ntp {state}"
  elif sys_type == "Darwin":  # macOS
    state = "on" if enable else "off"
    cmd = f"systemsetup -setusingnetworktime {state}"
  else:
    return

  subprocess.run(
      cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
  )


def set_sys_time(dt: datetime.datetime):
  """跨平台修改操作系统时间"""
  sys_type = platform.system()
  if sys_type == "Windows":
    # 使用 PowerShell 的 Set-Date，不受 Windows 区域日期格式（/ 或 -）差异的影响
    dt_str = dt.strftime("%Y-%m-%d %H:%M:%S")
    subprocess.run(
        f'powershell -Command "Set-Date -Date \'{dt_str}\'"',
        shell=True,
        check=True,
        stdout=subprocess.DEVNULL,
    )
  elif sys_type == "Linux":
    dt_str = dt.strftime("%Y-%m-%d %H:%M:%S")
    subprocess.run(f'date -s "{dt_str}"', shell=True, check=True)
  elif sys_type == "Darwin":  # macOS 格式: mmddHHMMyyyy.SS
    dt_str = dt.strftime("%m%d%H%M%Y.%S")
    subprocess.run(f"date {dt_str}", shell=True, check=True)
  else:
    raise NotImplementedError(f"不支持的操作系统: {sys_type}")


def main():
  parser = argparse.ArgumentParser(
      description="跨平台背景时间修改与自动矫正执行器"
  )
  parser.add_argument(
      "-t",
      "--time",
      required=True,
      help="目标背景时间，格式: 'YYYY-MM-DD HH:MM:SS' (例如 '2022-01-01 08:00:00')",
  )
  parser.add_argument(
      "-c",
      "--cmd",
      required=True,
      help="在此时间下要执行的脚本或命令 (例如 'python my_task.py')",
  )
  args = parser.parse_args()

  if not is_admin():
    print("❌ 权限不足：修改系统时间需要最高权限！")
    print(
        "👉 Windows 请右键 PowerShell 选择【以管理员身份运行】；Linux/macOS"
        " 请在命令前加 sudo。"
    )
    sys.exit(1)

  try:
    target_dt = datetime.datetime.strptime(args.time, "%Y-%m-%d %H:%M:%S")
  except ValueError:
    print(
        f"❌ 时间格式错误：{args.time}，请严格使用 'YYYY-MM-DD HH:MM:SS' 格式！"
    )
    sys.exit(1)

  # 记录修改前的真实时间，以及不受系统时间改动影响的单调递增时钟
  real_start = datetime.datetime.now()
  mono_start = time.monotonic()

  try:
    print(f"🔒 [1/3] 正在关闭自动时间同步，并将系统时间修改为: {target_dt}")
    toggle_ntp(False)
    set_sys_time(target_dt)

    print(f"🚀 [2/3] 开始执行目标任务: {args.cmd}")
    print("=" * 50)
    subprocess.run(args.cmd, shell=True)
    print("=" * 50)

  except KeyboardInterrupt:
    print("\n⚠️ 检测到手动中断 (Ctrl+C)，准备恢复真实系统时间...")
  except Exception as e:
    print(f"\n⚠️ 执行过程中出现异常: {e}")
  finally:
    # 计算任务真实消耗的秒数，精准补偿到初始真实时间上
    elapsed = time.monotonic() - mono_start
    corrected_time = real_start + datetime.timedelta(seconds=elapsed)

    print(
        f"⏱️ [3/3] 任务实际耗时 {elapsed:.2f} 秒，正在矫正并恢复系统时间为:"
        f" {corrected_time.strftime('%Y-%m-%d %H:%M:%S')}"
    )
    try:
      set_sys_time(corrected_time)
      toggle_ntp(True)
      print("✅ 系统时间已精准恢复，自动网络时间同步已重新开启！")
    except Exception as e:
      print(f"❌ 恢复时间失败，请手动检查系统时间设置: {e}")


if __name__ == "__main__":
  main()
