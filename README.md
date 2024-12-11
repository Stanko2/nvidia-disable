# NVIDIA disable

This script hides the NVIDIA GPU for certain applications, that use it by default.

## Used tweaks

1. sets the default GPU to render the desktop to the integrated Intel GPU
2. uses firejail to run applications with the NVIDIA GPU hidden, so that it can be suspended

## Usage

1. Install dependencies: `firejail`, `mesa-vulkan-layers`, `vulkan-intel`.
2. Run the script: `sudo python setup.py`


### limitations

- `discord` doesn't work with the NVIDIA GPU hidden, fails with the error (the script doesn't hide the GPU for discord):
```pcilib: Cannot open /sys/bus/pci/devices/0000:01:00.0/vendor: Permission denied```
