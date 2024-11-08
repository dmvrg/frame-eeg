# frame-eeg

Brilliant Labs' Frame AI glasses test with Muse EEG headbands  

![Devices](assets/devices.jpg)

This simple proof-of-concept test provides real-time EEG band power (Delta, Theta, Alpha, Beta, Gamma waves) and mental state values (Relaxation, Focus, Stress, and Drowsiness), displayed directly on the Frame AI glasses using BrainFlow, with additional desktop visualization via PyQtGraph.

During streaming, the user can toggle between viewing band powers and mental state estimations with a single tap on the temple of the glasses. This basic setup provides both wearable and desktop interfaces for real-time cognitive state monitoring.

## Hardware

 - **Brilliant Labs’ Frame AI glasses**  
https://brilliant.xyz/  
https://docs.brilliant.xyz/
- **Muse EEG headset**    
  https://choosemuse.com/ 
- **Desktop or laptop computer** with Bluetooth connectivity

Tested with Muse 2 and Muse S; theoretically compatible with any EEG device supported by BrainFlow's board-agnostic API.

## Dependencies

- **Python 3.8+**
- **Frame SDK** (SDK for Frame AI glasses)  
https://pypi.org/project/frame-sdk/  
- **BrainFlow** (EEG data processing)  
https://brainflow.org/  
- **PyQt5** & **PyQtGraph** (EEG data plotting on desktop, optional)  
https://www.pyqtgraph.org/
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
    
3. Run:
   
`frame_eeg-basic.py` : basic stream to Frame (no desktop visualization)  
`frame_eeg-pyqtgraph.py`  : stream and additional visualization on desktop with PyQtGraph

## Mental States

The mental states in the demo are just calculated based on EEG band power ratios and logarithmic transformations.

- **Relaxation (Alpha/Beta)**: Calculated using the ratio of Alpha to Beta band powers, transformed logarithmically to emphasize Alpha dominance, which is associated with relaxation.
- **Focus (Beta/Theta)**: Derived from the ratio of Beta to Theta band powers, with a logarithmic adjustment, as increased Beta relative to Theta often correlates with focused attention.
- **Stress (Beta/Alpha + Gamma)**: Determined using a combination of Beta and Gamma relative to Alpha, with an additional logarithmic transformation to capture increased arousal typically linked to stress.
- **Drowsiness (Delta/Alpha)**: Based on the ratio of Delta to Alpha band powers, logarithmically transformed to highlight increased Delta, which can indicate drowsiness or low alertness.





  
