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

# Constants for band power calculation
sampling_rate = BoardShim.get_sampling_rate(BoardIds.MUSE_S_BOARD)
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

async def main():
    async with Frame() as frame:
        # Register and start the BrainFlow session
        board.prepare_session()
        board.start_stream()

        print("Streaming EEG band powers and displaying mental states. Press Ctrl+C to stop.")
        
        # Initial values for toggle states
        show_states = True
        last_tap_time = 0  # Track the last tap time
        debounce_time = 0.3  # 300 milliseconds debounce

        # Define the tap callback function as synchronous
        def on_tap():
            nonlocal show_states, last_tap_time
            current_time = time.time()
            # Check if enough time has passed since the last tap
            if current_time - last_tap_time > debounce_time:
                show_states = not show_states
                last_tap_time = current_time  # Update last tap time
                print("Tapped, show_states is now:", show_states)
        
        # Register the tap callback function once
        await frame.motion.run_on_tap(callback=on_tap)

        try:
            while True:
                # Retrieve the latest 256 samples (1 second of data at 256 Hz)
                data = board.get_current_board_data(256)

                # Calculate and merge band power for each frequency band
                merged_band_powers = {}
                for band_name, (low_freq, high_freq) in bands.items():
                    band_powers = []
                    for channel in range(1, 5):  # Assuming channels 1 to 4 are EEG
                        eeg_channel_data = data[channel, :]
                        
                        # Apply bandpass filter to isolate the frequency band
                        DataFilter.perform_bandpass(eeg_channel_data, sampling_rate, low_freq, high_freq, 4, FilterTypes.BUTTERWORTH.value, 0)
                        
                        # Calculate power as the variance of the filtered signal
                        band_power = np.var(eeg_channel_data)
                        band_powers.append(band_power)

                    # Merge channels by averaging their band powers
                    merged_band_powers[band_name] = np.mean(band_powers)

                # Convert each band's power to dB and normalize dynamically
                db_band_powers = {}
                for band_name, power in merged_band_powers.items():
                    dB_value = 10 * np.log10(power + 1e-6)

                    # Update min/max for dynamic normalization
                    min_val, max_val = band_min_max[band_name]
                    band_min_max[band_name] = [min(min_val, dB_value), max(max_val, dB_value)]

                    # Normalize to a 50-100 range
                    if max_val > min_val:
                        normalized_value = 50 + 50 * (dB_value - min_val) / (max_val - min_val)
                    else:
                        normalized_value = 50

                    db_band_powers[band_name] = normalized_value

                # Get powers in linear scale
                alpha_power = 10 ** (db_band_powers["Alpha"] / 10)
                beta_power = 10 ** (db_band_powers["Beta"] / 10)
                gamma_power = 10 ** (db_band_powers["Gamma"] / 10)
                delta_power = 10 ** (db_band_powers["Delta"] / 10)
                theta_power = 10 ** (db_band_powers["Theta"] / 10)

                # Calculate mental states with adjusted scaling
                # Relaxation as log(alpha/beta)
                alpha_beta_ratio = alpha_power / (beta_power + 1e-6)
                log_alpha_beta_ratio = np.log1p(alpha_beta_ratio)
                alpha_beta_log_ratios.append(log_alpha_beta_ratio)
                relaxation_value = (log_alpha_beta_ratio - min(alpha_beta_log_ratios)) / (max(alpha_beta_log_ratios) - min(alpha_beta_log_ratios) + 1e-6) * 100

                # Focus as log(beta/theta)
                beta_theta_ratio = beta_power / (theta_power + 1e-6)
                log_beta_theta_ratio = np.log1p(beta_theta_ratio)
                beta_theta_focus_ratios.append(log_beta_theta_ratio)
                focus_value = (log_beta_theta_ratio - min(beta_theta_focus_ratios)) / (max(beta_theta_focus_ratios) - min(beta_theta_focus_ratios) + 1e-6) * 100

                # Stress as log(beta/alpha * gamma)
                combined_beta_gamma = (beta_power / (alpha_power + 1e-6)) * (gamma_power + 1e-6)
                log_stress_ratio = np.log1p(combined_beta_gamma)
                beta_alpha_stress_ratios.append(log_stress_ratio)
                stress_value = (log_stress_ratio - min(beta_alpha_stress_ratios)) / (max(beta_alpha_stress_ratios) - min(beta_alpha_stress_ratios) + 1e-6) * 100

                # Drowsiness as log(delta/alpha)
                delta_alpha_ratio = delta_power / (alpha_power + 1e-6)
                log_delta_alpha_ratio = np.log1p(delta_alpha_ratio)
                delta_alpha_drowsiness_ratios.append(log_delta_alpha_ratio)
                drowsiness_value = (log_delta_alpha_ratio - min(delta_alpha_drowsiness_ratios)) / (max(delta_alpha_drowsiness_ratios) - min(delta_alpha_drowsiness_ratios) + 1e-6) * 100

                # Print normalized band powers and mental states to terminal
                print("Band Powers (as %):", {band: f"{value:.1f}%" for band, value in db_band_powers.items()})
                print("Mental States (as %):", {
                    "Relaxation": f"{relaxation_value:.1f}%",
                    "Focus": f"{focus_value:.1f}%",
                    "Stress": f"{stress_value:.1f}%",
                    "Drowsiness": f"{drowsiness_value:.1f}%"
                })

                # Display EEG bands or mental states based on toggle
                if not show_states:
                    await frame.display.show_text(
                        f"D: {db_band_powers['Delta']:.1f}%  T: {db_band_powers['Theta']:.1f}%  A: {db_band_powers['Alpha']:.1f}%\nB: {db_band_powers['Beta']:.1f}%  G: {db_band_powers['Gamma']:.1f}%", 
                        align=Alignment.MIDDLE_CENTER
                    )
                else:
                    await frame.display.show_text(
                        f"Relax: {relaxation_value:.1f}%  Focus: {focus_value:.1f}%\nStress: {stress_value:.1f}%  Drowsiness: {drowsiness_value:.1f}%", 
                        align=Alignment.MIDDLE_CENTER
                    )

                await asyncio.sleep(0.1)

        except KeyboardInterrupt:
            print("\nStopping the stream.")
        finally:
            board.stop_stream()
            board.release_session()
            print("Session ended.")

asyncio.run(main())
