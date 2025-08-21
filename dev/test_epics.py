from epics import caget
import matplotlib.pyplot as plt

data = caget("OTRS:DIAG0:420:Image:ArrayData", timeout=5)
n_rows = caget("OTRS:DIAG0:420:ArraySize1_RBV", timeout=5)
n_cols = caget("OTRS:DIAG0:420:ArraySize0_RBV", timeout=5)

plt.imshow(data.reshape(n_rows, n_cols), cmap="gray")
plt.colorbar()
plt.show()
