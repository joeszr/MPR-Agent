"""check_IBE —— 带内发射(IBE)检测（check_IBE.m 的 Python 版）。

三项 General 限值取最大（最宽松）：

    IBEP1 = -25 - 10log10(NRB/lcrb)
    IBEP2 = 20log10(EVMLevel/100) - 3
    IBEP3 = -57 + 10log10(scs/15) - 10log10(outputpower/lcrb)

分配贴着载波边沿时（``rbstart == 0`` 或 ``rbend == NRB-1``）没有相邻 RB 可测，
直接判通过——与原 .m 一致。
"""

from __future__ import annotations

import numpy as np

from matlab_builtins import log10


def check_IBE(rbstart, rbend, NRB, lcrb, scs, scs_step, EVMLevel, outputpower111,
              carrier_position, aa11, cc11, orgin_aver_power111):
    """``check_IBE.m`` – in-band emission check against the unallocated RBs.

    Edge allocations (``rbstart == 0`` or ``rbend == NRB-1``) are not measurable
    with this indexing scheme and are declared a pass, exactly as in MATLAB.
    """
    psd = np.asarray(orgin_aver_power111).ravel()

    if rbstart > 0 and rbend < NRB - 1:
        IBEP1 = -25 - 10 * log10(NRB / lcrb)
        IBEP2 = 20 * log10(EVMLevel / 100) - 3
        IBEP3 = -57 + 10 * log10(scs / 15) - 10 * log10(outputpower111 / lcrb)
        IBElimit1 = np.maximum(IBEP1, IBEP2)
        IBElimit = np.maximum(IBElimit1, IBEP3)

        IBEPOWER = psd[np.asarray(carrier_position) - 1]
        IBEPOWERAVER = 10 * log10((np.mean(IBEPOWER) * 12 * scs_step)) + 1

        IBENONALLEFT = psd[int(aa11 - 12 * scs_step - 1) - 1:int(aa11 - 2)]
        IBENONALRIGHT = psd[int(cc11 + 2) - 1:int(cc11 + 12 * scs_step + 1)]

        IBEPOWERAVERLEFT = 10 * log10((np.mean(IBENONALLEFT) * 12 * scs_step))
        IBEPOWERAVERRIGHT = 10 * log10((np.mean(IBENONALRIGHT) * 12 * scs_step))

        IBELEFT = IBEPOWERAVERLEFT - IBEPOWERAVER
        IBERIGHT = IBEPOWERAVERRIGHT - IBEPOWERAVER

        return 1 if (IBELEFT <= IBElimit and IBERIGHT <= IBElimit) else 0

    return 1
