import numpy as np
import matplotlib.pyplot as plt
import sys

with open(sys.argv[1],"r") as f:
    s = f.read().split("\n")

samples = []
for i in range(len(samples)-1):
    try:
        samples[i] = int(samples[i])
    except: pass

plt.plot(n)
plt.show()
