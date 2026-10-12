import numpy as np
import matplotlib.pyplot as plt
import scipy.signal as sig
from scipy.signal import ShortTimeFFT
import scipy.io.wavfile as wav

(Fs, x) = wav.read("sa1_.wav")

Ts = 1 / Fs   # sampling period

# user selectable parameters
w_len = 30e-3  # 30 ms window length
w_hop = 2e-3  # 2 ms hop or update
multiplier = 16  # multiple of frame length for FFT


w_N = int(w_len / Ts)  # window length in no. of samples
hop_N = int(w_hop / Ts)  # hop in no. of samples
Nfft = int(2 ** np.ceil(np.log(multiplier * w_N) / np.log(2)))  # find next power of 2 just larger than 2 * w_N



# use Hamming window
win = sig.windows.hamming(w_N)

stft = ShortTimeFFT(win, hop_N, Fs, mfft = Nfft)

X = stft.spectrogram(x)
Xdb = 10 * np.log10(X)  # convert to dB to compress the dynamic range


# Plotting code

f = (np.arange(Nfft) / Nfft * Fs)[: Nfft // 2 + 1]  # frequency axis values
t = np.arange(X.shape[1]) * w_hop # time axis values


plt.close("all")
plt.figure(figsize = (10, 4))

mesh = plt.pcolormesh(t, f, Xdb, cmap = "magma", rasterized = True)

# Increase and decreasing detail using dynamic range

dr = 100  # dynamic range in dB from peak (increase for more detail)

mx = np.max(Xdb)
mn = mx - dr
mesh.set_clim(vmin = mn, vmax = mx)

plt.xlim(np.min(t), np.max(t))
plt.ylim(np.min(f), np.max(f))
plt.xlabel('Time (s)')
plt.ylabel('Frequency (Hz)')
plt.grid(True)
plt.tight_layout()
plt.savefig("spectro.svg")
plt.show(block=False)


