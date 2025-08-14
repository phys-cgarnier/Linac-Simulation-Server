from lcls_tools.common.devices.reader import create_screen
import matplotlib.pyplot as plt
import epics
screen = create_screen('DIAG0', 'OTRDG02')

print(epics.caget('OTRS:DIAG0:420:PNEUMATIC'))
print(epics.caget('OTRS:DIAG0:420:Image:ArraySize0_RBV'))
epics.caput('OTRS:DIAG0:420:Image:ArrayData',1)
'''
print(screen)
print(screen.n_rows)
img = screen.image
print(img.shape)
plt.imshow(img)
plt.tight_layout()
plt.show()
'''