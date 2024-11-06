# frame-eeg

Simple integration of Brilliant Labs’ Frame AI glasses with Muse EEG headbands  

![Devices](assets/devices.jpg)

This project provides real-time EEG band power (Alpha, Beta, Delta, Gamma, Theta waves) and mental state values (Relaxation, Focus, Stress, and Drowsiness) displayed directly on the Frame AI glasses using BrainFlow, with additional desktop visualization via PyQtGraph.

During streaming, users can toggle between viewing band powers and mental state estimations with a single tap on the temple of the glasses. This basic setup provides both wearable and desktop interfaces for real-time cognitive state monitoring.

## Hardware

- **Muse EEG headset**    
  https://choosemuse.com/  
- **Brilliant Labs’ Frame AI glasses**  
https://brilliant.xyz/  
https://docs.brilliant.xyz/  

Tested with Muse 2 and Muse S; theoretically compatible with any EEG device supported by BrainFlow's board-agnostic API.

## Dependencies

- **Python 3.8+**
- **Frame SDK** (SDK for Frame AI glasses)  
https://pypi.org/project/frame-sdk/  
- **BrainFlow** (EEG data processing)  
https://brainflow.org/  
- **PyQt5** & **PyQtGraph** (EEG data plotting on desktop, optional)  
- **asyncio, numpy**  


## Installation

1. Clone this repository:
    
    ```bash
    git clone https://github.com/dmvrg/frame-eeg.git
    ```
    
2. Install dependencies:
    
    ```bash
    pip install numpy brainflow frame-sdk pyqt5 pyqtgraph 
    ```
    
3. Run 
`frame_eeg-basic.py` : direct stream to Frame (no desktop visualization)
`frame_eeg-pyqtgrph.py`  : stream and additional visualization on desktop with PyQtGraph

## Mental States

The mental states are calculated based on EEG band power ratios and logarithmic transformations.

- **Relaxation (Alpha/Beta)**: Calculated using the ratio of Alpha to Beta band powers, transformed logarithmically to emphasize Alpha dominance, which is associated with relaxation.
- **Focus (Beta/Theta)**: Derived from the ratio of Beta to Theta band powers, with a logarithmic adjustment, as increased Beta relative to Theta often correlates with focused attention.
- **Stress (Beta/Alpha + Gamma)**: Determined using a combination of Beta and Gamma relative to Alpha, with an additional logarithmic transformation to capture increased arousal typically linked to stress.
- **Drowsiness (Delta/Alpha)**: Based on the ratio of Delta to Alpha band powers, logarithmically transformed to highlight increased Delta, which can indicate drowsiness or low alertness.





  
