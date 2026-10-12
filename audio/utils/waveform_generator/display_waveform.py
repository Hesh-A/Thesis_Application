import numpy as np
import matplotlib.pyplot as plt
import pyqtgraph as pg


def build_pyqtgraph_waveform(sample_rate, audio_data, start_time=0.0, end_time=0.0):
    # Plot one amplitude per sample, averaging channels when the input is stereo.
    if audio_data.ndim == 2:
        audio_data = audio_data.mean(axis=1)

    # Convert the requested seconds to sample positions; zero end_time means the full remainder.
    start_index = int(start_time * sample_rate)
    end_index = int(end_time * sample_rate) if end_time > 0 else len(audio_data)
    visible_audio = audio_data[start_index:end_index].astype(np.float32)
    if len(visible_audio) == 0:
        raise ValueError("The selected time range does not contain any samples.")

    # Keep the x-axis in recording time rather than restarting at zero for a cropped view.
    time = start_time + np.arange(len(visible_audio)) / sample_rate
    waveform = pg.PlotWidget()
    waveform.setBackground("#f7f8fa")
    waveform.getPlotItem().hideButtons()
    waveform.setLabel("left", "Amplitude")
    waveform.setLabel("bottom", "Time", units="s")
    waveform.showGrid(x=True, y=True, alpha=0.2)
    waveform.plot(time, visible_audio, pen=pg.mkPen("#176b87", width=1))
    waveform.setXRange(time[0], time[-1], padding=0)

    return waveform, (time[0], time[-1])


def build_mono_waveform_figure(sample_rate, audio_data, start_time: float = 0, end_time: float = 0):
    # if audio has two channels, so average them into one mono channel.
    if audio_data.ndim == 2:
        mono_audio = audio_data.mean(axis=1)
    else:
        mono_audio = audio_data

    # Create one time value for every sample.
    time = np.arange(len(mono_audio)) / sample_rate

    start_index = int(start_time * sample_rate) if start_time != 0 else 0
    end_index = int(end_time * sample_rate) if end_time != 0 else len(mono_audio)

    visible_time = time[start_index:end_index]
    visible_audio = mono_audio[start_index:end_index]

    if len(visible_time) == 0:
        raise ValueError("The selected time range does not contain any samples.")

    figure, axis = plt.subplots(figsize=(13, 4), layout="constrained")
    figure.patch.set_facecolor("#f7f8fa")
    axis.set_facecolor("#ffffff")

    axis.plot(visible_time, visible_audio, color="#176b87", linewidth=0.7)
    axis.fill_between(visible_time, visible_audio, 0, color="#176b87", alpha=0.18)
    axis.axhline(0, color="#6b7280", linewidth=0.7)
    axis.set_xlim(visible_time[0], visible_time[-1])
    axis.set_ylabel("Amplitude")
    axis.grid(True, color="#d1d5db", linewidth=0.6, alpha=0.8)

    return figure


def display_mono_waveform(sample_rate, audio_data, start_time: float = 0, end_time: float = 0):
    figure = build_mono_waveform_figure(sample_rate, audio_data, start_time, end_time)
    plt.show()
    return figure


#testing

if __name__ == "__main__":
    try:
        from audio.utils.waveform_generator.read_audio import read_audio, AUDIO_PATH
    except ModuleNotFoundError:
        from read_audio import read_audio, AUDIO_PATH

    sample_rate, audio_data = read_audio(AUDIO_PATH)
    display_mono_waveform(sample_rate, audio_data, start_time=0.5, end_time=3)
