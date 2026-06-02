# Windows-Enclave-API-Abuse
演示如何通过 Windows 未公开的 LdrCallEnclave API 执行内存中的 shellcode，并探讨此类技术的检测与防御方法。

# Enclave Shellcode Loader PoC

**教育目的**：演示如何通过 Windows 未公开的 `LdrCallEnclave` API 执行内存中的 shellcode，并探讨此类技术的检测与防御方法。

> ⚠️ **严格声明**  
> 本项目仅供安全研究人员和防御者在受控的隔离环境中进行学习与分析。  
> **禁止**将代码用于任何未经授权的系统入侵、恶意软件制作或其他非法活动。  
> 使用者需遵守所在地法律法规，并对自己的行为负责。

---

## 概述

现代恶意软件经常滥用 Windows 的可信执行环境（VBS Enclave）相关函数来绕过用户态 Hook 和行为监控。  
`LdrCallEnclave` 是 `ntdll.dll` 中的一个未公开 API，本意为在 Enclave 中执行受信任代码，但实际可被用于执行任意 shellcode，且调用栈干净，不易被常规安全软件检测。

本 PoC 展示了一种典型的攻击手法：

1. 使用 `VirtualAlloc` 分配 `PAGE_EXECUTE_READWRITE` 内存。  
2. 将自包含的 shellcode（弹出计算器）拷贝到该内存区域。  
3. 通过 `LdrCallEnclave` 创建线程并执行 shellcode。  
4. Shellcode 自身完成 API 解析（`WinExec` 与 `ExitThread`），干净退出。

项目采用 **Python + ctypes** 实现，直观展示整个调用链。

---

## 技术细节

### Shellcode 功能
硬编码的 x64 shellcode 包含以下逻辑：
- 遍历 PEB 找到 `kernel32.dll` 基址。
- 解析导出表获取 `LoadLibraryA`、`WinExec` 和 `ExitThread` 的函数地址。
- 调用 `WinExec("calc.exe", SW_SHOWNORMAL)`。
- 调用 `ExitThread(0)` 正常退出，避免崩溃。

### 滥用 API 分析
| API | 作用 | 恶意用途 |
|-----|------|----------|
| `VirtualAlloc` | 分配可执行内存 | 动态存放 shellcode，逃避静态扫描 |
| `LdrCallEnclave` | 在类似 Enclave 的上下文中调用函数指针 | 创建用户态线程执行任意代码，绕开部分 EDR 的 `NtCreateThreadEx` Hook |
| `PAGE_EXECUTE_READWRITE` | 内存保护属性 | 同时具备写与执行权限，符合 shellcode 加载典型特征 |

### 为什么选择 `LdrCallEnclave`？
- 调用链为 `ntdll!LdrCallEnclave` → `ntdll!RtlCreateUserThread`（或直接跳转），许多安全产品未在此路径上设置有效 Hook。  
- 相比直接使用 `CreateThread` 或 `NtCreateThreadEx`，可以绕过部分行为监控规则。  
- 在未启用完整 VBS 的系统上，该函数仍然可以工作，只是没有真正的 Enclave 保护。

---

## 使用说明

### 环境要求
- **操作系统**：Windows 10 1809 或更高版本（64 位）
- **Python**：64 位 Python 3.x（必须与系统架构一致）
- **权限**：普通用户权限即可，无需管理员特权

### 运行步骤
1. 克隆仓库：
   ```bash
   git clone https://github.com/your-org/enclave-loader-poc.git
   cd enclave-loader-poc
   ```
2. 直接运行脚本（无需额外依赖）：
   ```cmd
   python enclave_loader_poc_hardcoded.py
   ```
3. 预期结果：  
   - 终端输出内存分配地址、函数调用状态等信息。  
   - 弹出 Windows 计算器（`calc.exe`）。  
   - 脚本正常结束，无残留线程。

> **注意**：某些杀毒软件可能会拦截 `VirtualAlloc` 分配 `RWX` 内存的行为，或直接将脚本标识为恶意。若需测试，请在虚拟机中关闭实时防护或添加临时排除项。

---

## 检测与防御建议

### 主机侧检测特征
- 调用栈中出现 `LdrCallEnclave` 且来源非微软签名进程。  
- 进程同时分配大量 `PAGE_EXECUTE_READWRITE` 内存并写入可执行代码。  
- 父进程为解释器（如 `python.exe`）或非标准可执行文件，却进行内存分配和线程创建操作。

### 防御措施
1. **启用内存完整性（HVCI）**：阻止动态分配 `RWX` 内存，强制使用 `W^X` 策略。  
2. **部署 EDR 并监控罕见 API**：对 `LdrCallEnclave`、`VirtualAlloc` 等敏感调用设置警报规则。  
3. **限制脚本宿主网络权限**：减少攻击面，防止 Python 等脚本引擎被滥用以加载载荷。  
4. **应用程序控制（WDAC）**：只允许受信任的 DLL 和可执行文件运行。

---

## 文件结构

```
.
├── enclave_loader_poc_hardcoded.py    # 主 PoC 脚本（硬编码 shellcode）
├── LICENSE                            # 开源许可证
└── README.md                          # 本文件
```

---

## 免责声明

本项目仅为展示技术原理，**不提供任何恶意载荷或完整的攻击链**。作者不对因滥用本代码造成的任何后果负责。如果您发现本代码被用于非法目的，请立即停止使用并向相关部门报告。

---

## 参考资料
- [Windows Internals, Part 2 (7th Edition)](https://www.microsoftpressstore.com/)
- [Mitigating Process Injection with the Windows 10 Security Features](https://docs.microsoft.com/en-us/windows/security/threat-protection/)
- [滥用 VBS Enclave 运行恶意代码](https://cn-sec.com/archives/3836257.html) （示例说明）

---

**请负责任地研究，共同提升网络安全水平。**
