# Legacy Matplotlib import preserved for rollback:
# import matplotlib.pyplot as plt
import numpy as np
import pyqtgraph as pg
import scipy.signal as sig
from PyQt6.QtCore import QRectF
# from scipy.io import wavfile
from scipy.signal import ShortTimeFFT


# util function for the "gray" colormap in pyqtgraph
def get_pyqtgraph_colormap_lut(colormap):
    if colormap == "gray":
        color_map = pg.ColorMap(
            [0.0, 1.0],
            [(0, 0, 0), (255, 255, 255)],
        )
    else:
        color_map = pg.colormap.get(colormap)

    return color_map.getLookupTable(nPts=256)

# Function to calculate the spectrogram of an audio signal
def calculate_spectrogram(
    sample_rate,
    audio_data,
    window_length_ms: float = 30.0,
    hop_ms: float = 2.0,
    fft_multiplier: int = 16,
    window_type: str = "hamming",
):
    ts = 1 / sample_rate
    w_len = window_length_ms / 1000.0
    w_hop = hop_ms / 1000.0
    multiplier = fft_multiplier

    w_n = int(w_len / ts)
    hop_n = int(w_hop / ts)
    nfft = int(2 ** np.ceil(np.log(multiplier * w_n) / np.log(2)))

    window_functions = {
        "hamming": sig.windows.hamming,
        "hann": sig.windows.hann,
        "blackman": sig.windows.blackman,
        "boxcar": sig.windows.boxcar,
    }
    win = window_functions.get(window_type, sig.windows.hamming)(w_n)
    stft = ShortTimeFFT(win, hop_n, sample_rate, mfft=nfft)
    x = stft.spectrogram(audio_data)
    #avoid log of zero by replacing zeros with the smallest positive float
    x = np.maximum(x, np.finfo(float).tiny)
    xdb = 10 * np.log10(x)

    f = (np.arange(nfft) / nfft * sample_rate)[: nfft // 2 + 1]
    t = np.arange(x.shape[1]) * w_hop

    return t, f, xdb

# Function to build a pyqtgraph spectrogram widget from spectrogram data
def build_pyqtgraph_spectrogram(
    times,
    frequencies,
    spectrogram_db,
    dynamic_range_db: float = 100.0,
    colormap: str = "magma",
):
    times = np.asarray(times)
    frequencies = np.asarray(frequencies)
    image_data = np.asarray(spectrogram_db[: len(frequencies), :])
    maximum_db = float(np.max(image_data))

    plot = pg.PlotWidget()
    plot.setBackground("#f7f8fa")
    plot.setLabel("left", "Frequency", units="Hz")
    plot.setLabel("bottom", "Time", units="s")
    plot.getPlotItem().getAxis("left").enableAutoSIPrefix(False)
    plot.showGrid(x=True, y=True, alpha=0.2)
    plot.getPlotItem().hideButtons()

    image = pg.ImageItem(axisOrder="row-major")
    image.setImage(
        image_data,
        autoLevels=False,
        levels=(maximum_db - dynamic_range_db, maximum_db),
    )
    image.setRect(
        QRectF(
            float(times[0]),
            float(frequencies[0]),
            float(times[-1] - times[0]),
            float(frequencies[-1] - frequencies[0]),
        )
    )
    image.setLookupTable(get_pyqtgraph_colormap_lut(colormap))
    plot.addItem(image)
    plot.setXRange(float(times[0]), float(times[-1]), padding=0)
    plot.setYRange(float(frequencies[0]), float(frequencies[-1]), padding=0)

    return plot, image, maximum_db

# ----------------------------------------------------------------------------------
# Following functions are related to building spectrogram figures using matplotlib
# ----------------------------------------------------------------------------------


# Function to build a matplotlib spectrogram figure from audio data
# def build_spectrogram_figure(
#     sample_rate,
#     audio_data,
#     window_length_ms: float = 30.0,
#     hop_ms: float = 2.0,
#     fft_multiplier: int = 16,
#     dynamic_range_db: float = 100.0,
#     colormap: str = "magma",
# ):
#     t, f, xdb = calculate_spectrogram(
#         sample_rate,
#         audio_data,
#         window_length_ms=window_length_ms,
#         hop_ms=hop_ms,
#         fft_multiplier=fft_multiplier,
#     )

#     return build_spectrogram_figure_from_data(t, f, xdb, dynamic_range_db, colormap)

# Function to build a matplotlib spectrogram figure from precomputed spectrogram data
# def build_spectrogram_figure_from_data(
#     times,
#     frequencies,
#     spectrogram_db,
#     dynamic_range_db: float = 100.0,
#     colormap: str = "magma",
# ):
#     figure = plt.figure(figsize=(10, 4))

#     maximum_db = np.max(spectrogram_db)
#     minimum_db = maximum_db - dynamic_range_db
#     axis = figure.add_subplot()
#     spectrogram_image = axis.imshow(
#         spectrogram_db,
#         aspect="auto",
#         origin="lower",
#         extent=[times[0], times[-1], frequencies[0], frequencies[-1]],
#         cmap=colormap,
#         vmin=minimum_db,
#         vmax=maximum_db,
#     )

#     axis.set_xlim(times[0], times[-1])
#     axis.set_ylim(frequencies[0], frequencies[-1])
#     axis.set_xlabel("Time (s)")
#     axis.set_ylabel("Frequency (Hz)")
#     figure.tight_layout()

#     return figure, spectrogram_image

# def display_spectrogram(sample_rate, audio_data):
#     figure, _ = build_spectrogram_figure(sample_rate, audio_data)
#     plt.show()
    


# Legacy Matplotlib standalone entry point preserved for rollback:
# if __name__ == "__main__":
#     sample_rate, audio_data = wavfile.read(DEFAULT_AUDIO_PATH)
#     display_spectrogram(sample_rate, audio_data)


