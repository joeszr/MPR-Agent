"""figure_plot —— 把一维结果向量还原成二维 MPR 地图（figure_plot.m 的 Python 版）。

MATLAB 版本从工作区变量 ``mr_data`` 取数据（每行一个 RB 配置的 MPR，单位 dB），
把负值截零、四舍五入成整数 dB 后按类别画散点：横轴 RB start，纵轴 LCRB。

Python 版本从结果文件读同一个向量：

    python plots/figure_plot.py 1022-1533-100MHZ-256QAM.npz
    python plots/figure_plot.py 1022-1533-100MHZ-256QAM.npz --rated-power 26

主程序存的是"最大输出功率"(dBm)；给 --rated-power 26 就按 MPR = max(0, 26 - P)
换算（工程说明文档 8.2 节说这一步原来要手工做）。

没装 matplotlib 时不报错：同样的数据写成 CSV，并提示安装命令。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np


def build_map(mpr_values, NRB):
    """按 .m 里 while 循环的相同顺序生成 ``RBstrat`` / ``LCRB``。"""
    n = (1 + NRB) * NRB // 2          # 总共的 RB 起止组合数
    RBstrat = np.zeros(n)
    LCRB = np.zeros(n)
    xh = 0
    rbstart = -1
    while rbstart < NRB - 1:
        rbstart += 1
        rbend = rbstart - 1
        while rbend < NRB - 1:
            rbend += 1
            RBstrat[xh] = rbstart
            LCRB[xh] = rbend - rbstart + 1
            xh += 1

    MPR = np.array(mpr_values, dtype=float).ravel()
    MPR[MPR <= 0] = 0                 # 负值截零

    # 确保长度匹配（.m 用 minLen 静默截断）
    minLen = min(MPR.size, n)
    return RBstrat[:minLen], LCRB[:minLen], MPR[:minLen]


def load_mpr(path, key):
    """从 .npz / .npy / .csv 里取出一个向量。"""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".npz":
        with np.load(path) as data:
            if key not in data:
                raise KeyError(f"{key!r} 不在 {path} 里，可用的有 {list(data)}")
            return np.asarray(data[key]).ravel()
    if suffix == ".npy":
        return np.asarray(np.load(path)).ravel()
    if suffix == ".csv":
        header = path.read_text(encoding="utf-8").splitlines()[0].split(",")
        raw = np.atleast_1d(np.loadtxt(path, delimiter=",", skiprows=1))
        if raw.ndim == 2:
            return raw[:, header.index(key) if key in header else 0].ravel()
        return raw.ravel()
    return np.atleast_1d(np.loadtxt(path)).ravel()


def write_csv(path, RBstrat, LCRB, MPR):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write("RBstart,LCRB,MPR\n")
        for a, b, c in zip(RBstrat, LCRB, MPR):
            fh.write(f"{a:g},{b:g},{c:g}\n")
    return str(path)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="画 MPR 地图（figure_plot.m 的 Python 版）")
    parser.add_argument("results", help="结果文件（.npz / .npy / .csv）")
    parser.add_argument("--key", default="MPR_results", help="要画哪个变量")
    parser.add_argument("--nrb", type=int, default=273, help="RB 总数（.m 里写死 273）")
    parser.add_argument("--rated-power", type=float, default=None,
                        help="额定功率 (dBm)；给了就按 MPR=max(0, 额定 - P) 换算")
    parser.add_argument("--title", default=None, help="图标题")
    parser.add_argument("--out", default=None, help="输出图片名")
    parser.add_argument("--csv", default=None, help="同时导出的 CSV 名")
    args = parser.parse_args(argv)

    path = Path(args.results)
    values = load_mpr(path, args.key)
    if args.rated_power is not None:
        values = np.maximum(0.0, args.rated_power - values)

    RBstrat, LCRB, MPR = build_map(values, args.nrb)

    out_png = Path(args.out) if args.out else path.with_name(path.stem + "_mpr_map.png")
    out_csv = Path(args.csv) if args.csv else path.with_name(path.stem + "_mpr_map.csv")
    write_csv(out_csv, RBstrat, LCRB, MPR)

    try:
        import matplotlib
        import matplotlib.pyplot as plt
    except Exception:
        print("提示: 没有安装 matplotlib，图没有画出来；同样的数据已写入 CSV。")
        print("      pip install matplotlib 之后重跑即可出图。")
        print(f"      数据: {out_csv}")
        return 0

    MPR2 = np.round(MPR)                      # 分类标签（整数值）
    uniqueVals = np.unique(MPR2)
    numGroups = len(uniqueVals)
    try:
        cmap = matplotlib.colormaps["viridis"]
    except AttributeError:                    # 老版本 matplotlib
        cmap = plt.get_cmap("viridis")
    colors = cmap(np.linspace(0, 1, max(numGroups, 2)))

    fig, ax = plt.subplots(figsize=(9, 6))
    handles = []
    for i, val in enumerate(uniqueVals):
        idx = MPR2 == val
        handles.append(ax.scatter(RBstrat[idx], LCRB[idx], s=36, color=colors[i],
                                  marker="o", linewidths=0,
                                  label=f"MPR = {int(val)} dB"))
    ax.set_xlabel("RB Start")
    ax.set_ylabel("LCRB (Number of RBs)")
    ax.set_title(args.title or "CP-OFDM preliminary MPR simulation results")
    if handles:
        ax.legend(loc="best", fontsize=8)

    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=150, bbox_inches="tight")
    print(f"figure saved to: {out_png}")
    plt.close(fig)
    return 0


if __name__ == "__main__":
    sys.exit(main())
