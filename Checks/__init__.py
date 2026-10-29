"""Checks —— 指标检测(EVM / ACLR / SEM / IBE)包。

原工程根目录下散放的 ``check_*.py`` 与 ``mirror_check.py`` 归档到此。包内模块之间用
相对导入互相引用；对上层的 ``matlab_builtins`` 用绝对导入（运行脚本时项目根目录已在
``sys.path`` 上）。

对外入口：

    from Checks.check_ACLR import check_ACLR
    from Checks.check_EVM_CP import check_EVM_CP
    from Checks.check_EVM_DFT import check_EVM_DFT
    from Checks.check_IBE import check_IBE
    from Checks.check_SEM_FR1 import check_SEM_FR1
    from Checks.check_SEM_FR2 import check_SEM_FR2

``mirror_check`` 不是检测函数，而是可以单独运行的诊断脚本：

    python Checks/mirror_check.py
"""
