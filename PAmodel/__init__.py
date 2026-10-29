"""PAmodel —— 功放(PA)模型包。

原工程根目录下散放的 ``apply_pa_model.py``、``pa_*.py``、``HZW_HB_*.py`` 归档到此。
包内模块之间用相对导入互相引用；对上层的 ``matlab_builtins`` 用绝对导入
（运行脚本时项目根目录已在 ``sys.path`` 上）。

对外入口：

    from PAmodel.apply_pa_model import apply_pa_model
    output = apply_pa_model(signal_window, k, PA_MODEL_TYPE)
"""
