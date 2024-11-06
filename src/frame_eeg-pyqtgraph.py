import sys
from PyQt5 import QtWidgets
import pyqtgraph as pg
from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds
from brainflow.data_filter import DataFilter, FilterTypes
import numpy as np
from collections import deque
import asyncio
import time
from frame_sdk import Frame
from frame_sdk.display import Alignment

# Initialize BrainFlow
BoardShim.enable_board_logger()
params = BrainFlowInputParams()
board = BoardShim(BoardIds.MUSE_S_BOARD, params)
sampling_rate = BoardShim.get_sampling_rate(BoardIds.MUSE_S_BOARD)

# Constants for band power calculation
bands = {
    "Delta": (0.5, 4),
    "Theta": (4, 8),
    "Alpha": (8, 12),
    "Beta": (12, 30),
    "Gamma": (30, 50)
}

# Rolling storage for state values with capped length to ensure a moving window
alpha_beta_log_ratios = deque(maxlen=100)
beta_theta_focus_ratios = deque(maxlen=100)
beta_alpha_stress_ratios = deque(maxlen=100)
delta_alpha_drowsiness_ratios = deque(maxlen=100)

# Dynamic min-max range for each band
band_min_max = {band: [np.inf, -np.inf] for band in bands}

# Initialize data structures for visualization with a 100-unit window
data_deques = {band: deque([0] * 100, maxlen=100) for band in bands.keys()}
state_deques = {"Relaxation": deque([0] * 100, maxlen=100), 
                "Focus": deque([0] * 100, maxlen=100), 
                "Stress": deque([0] * 100, maxlen=100), 
                "Drowsiness": deque([0] * 100, maxlen=100)}

# PyQtGraph layout setup
app = QtWidgets.QApplication(sys.argv)
win = pg.GraphicsLayoutWidget(show=True, title="Frame EEG")
win.resize(1200, 1000)

layout = win.ci  # Access the central item layout

brainwave_plot = layout.addPlot(row=0, col=0, colspan=2)
brainwave_plot.setTitle(
    "<span style='font-size: 16pt; color: red'>•</span> Delta  "
    "<span style='font-size: 16pt; color: purple'>•</span> Theta  "
    "<span style='font-size: 16pt; color: blue'>•</span> Alpha  "
    "<span style='font-size: 16pt; color: green'>•</span> Beta  "
    "<span style='font-size: 16pt; color: orange'>•</span> Gamma",
    size="16pt" 
)
brainwave_plot.setXRange(0, 75)
brainwave_plot.enableAutoRange(axis='y')
brainwave_plot.setPreferredHeight(600)

color_map = {
    "Delta": (255, 0, 0),       # Red
    "Theta": (128, 0, 128),     # Purple
    "Alpha": (0, 0, 255),       # Blue
    "Beta": (0, 128, 0),        # Green
    "Gamma": (255, 165, 0)      # Orange
}

curves = {band: brainwave_plot.plot(pen=pg.mkPen(color, width=2)) for band, color in color_map.items()}

# Add mental state plots in a 2x2 grid below the full-width plot
state_plots, state_curves = {}, {}
for idx, state in enumerate(state_deques.keys()):
    row = (idx // 2) + 1
    col = idx % 2
    state_plots[state] = layout.addPlot(row=row, col=col, title=f"{state}")
    state_plots[state].setTitle(f"<span style='font-size: 16pt'>{state}</span>")
    state_plots[state].setXRange(0, 75)
    state_plots[state].setYRange(0, 100)
    state_plots[state].setPreferredHeight(150)
    state_curves[state] = state_plots[state].plot(pen=pg.mkPen(width=2))

async def main():
    async with Frame() as frame:
        # Register and start BrainFlow session
        board.prepare_session()
        board.start_stream()

        print("Streaming EEG band powers and displaying mental states. Press Ctrl+C to stop.")
        
        show_states = True
        last_tap_time = 0
        debounce_time = 0.3

        def on_tap():
            nonlocal show_states, last_tap_time
            current_time = time.time()
            if current_time - last_tap_time > debounce_time:
                show_states = not show_states
                last_tap_time = current_time
                print("Tapped, show_states is now:", show_states)
        
        await frame.motion.run_on_tap(callback=on_tap)

        try:
            while True:
                data = board.get_current_board_data(256)
                merged_band_powers = {}

                for band_name, (low_freq, high_freq) in bands.items():
                    band_powers = []
                    for channel in range(1, 5):
                        eeg_channel_data = data[channel, :]
                        DataFilter.perform_bandpass(eeg_channel_data, sampling_rate, low_freq, high_freq, 4, FilterTypes.BUTTERWORTH.value, 0)
                        band_power = np.var(eeg_channel_data)
                        band_powers.append(band_power)
                    avg_band_power = np.mean(band_powers)
                    merged_band_powers[band_name] = avg_band_power

                db_band_powers = {}
                for band_name, power in merged_band_powers.items():
                    dB_value = 10 * np.log10(power + 1e-6)
                    min_val, max_val = band_min_max[band_name]
                    band_min_max[band_name] = [min(min_val, dB_value), max(max_val, dB_value)]

                    normalized_value = 50 + 50 * (dB_value - min_val) / (max_val - min_val) if max_val > min_val else 50
                    db_band_powers[band_name] = normalized_value
                    data_deques[band_name].append(normalized_value)

                alpha_power = 10 ** (db_band_powers["Alpha"] / 10)
                beta_power = 10 ** (db_band_powers["Beta"] / 10)
                gamma_power = 10 ** (db_band_powers["Gamma"] / 10)
                delta_power = 10 ** (db_band_powers["Delta"] / 10)
                theta_power = 10 ** (db_band_powers["Theta"] / 10)

                alpha_beta_ratio = alpha_power / (beta_power + 1e-6)
                log_alpha_beta_ratio = np.log1p(alpha_beta_ratio)
                alpha_beta_log_ratios.append(log_alpha_beta_ratio)
                relaxation_value = (log_alpha_beta_ratio - min(alpha_beta_log_ratios)) / (max(alpha_beta_log_ratios) - min(alpha_beta_log_ratios) + 1e-6) * 100

                beta_theta_ratio = beta_power / (theta_power + 1e-6)
                log_beta_theta_ratio = np.log1p(beta_theta_ratio)
                beta_theta_focus_ratios.append(log_beta_theta_ratio)
                focus_value = (log_beta_theta_ratio - min(beta_theta_focus_ratios)) / (max(beta_theta_focus_ratios) - min(beta_theta_focus_ratios) + 1e-6) * 100

                combined_beta_gamma = (beta_power / (alpha_power + 1e-6)) * (gamma_power + 1e-6)
                log_stress_ratio = np.log1p(combined_beta_gamma)
                beta_alpha_stress_ratios.append(log_stress_ratio)
                stress_value = (log_stress_ratio - min(beta_alpha_stress_ratios)) / (max(beta_alpha_stress_ratios) - min(beta_alpha_stress_ratios) + 1e-6) * 100

                delta_alpha_ratio = delta_power / (alpha_power + 1e-6)
                log_delta_alpha_ratio = np.log1p(delta_alpha_ratio)
                delta_alpha_drowsiness_ratios.append(log_delta_alpha_ratio)
                drowsiness_value = (log_delta_alpha_ratio - min(delta_alpha_drowsiness_ratios)) / (max(delta_alpha_drowsiness_ratios) - min(delta_alpha_drowsiness_ratios) + 1e-6) * 100

                print("Band Powers (as %):", {band: f"{value:.1f}%" for band, value in db_band_powers.items()})
                print("Mental States (as %):", {
                    "Relaxation": f"{relaxation_value:.1f}%",
                    "Focus": f"{focus_value:.1f}%",
                    "Stress": f"{stress_value:.1f}%",
                    "Drowsiness": f"{drowsiness_value:.1f}%"
                })

                for band_name, curve in curves.items():
                    curve.setData(data_deques[band_name])

                state_deques["Relaxation"].append(relaxation_value)
                state_deques["Focus"].append(focus_value)
                state_deques["Stress"].append(stress_value)
                state_deques["Drowsiness"].append(drowsiness_value)
                for state_name, curve in state_curves.items():
                    curve.setData(state_deques[state_name])

                display_text = (
                    f"D: {db_band_powers['Delta']:.1f}%  T: {db_band_powers['Theta']:.1f}%  "
                    f"A: {db_band_powers['Alpha']:.1f}%\nB: {db_band_powers['Beta']:.1f}%  G: {db_band_powers['Gamma']:.1f}%"
                    if not show_states else
                    f"Relax: {relaxation_value:.1f}% Focus: {focus_value:.1f}%\nStress: {stress_value:.1f}% Drowsiness: {drowsiness_value:.1f}%"
                )
                await frame.display.show_text(display_text, align=Alignment.MIDDLE_CENTER)

                QtWidgets.QApplication.processEvents()
                await asyncio.sleep(0.05)

        except KeyboardInterrupt:
            print("\nStopping the stream.")
        finally:
            board.stop_stream()
            board.release_session()
            print("Session ended.")

asyncio.run(main())
sys.exit(app.exec_())
