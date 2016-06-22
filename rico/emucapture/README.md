**EmuCapture** provides a socket interface for streaming screen capture data from Android emulators. It is meant to be used in place of the [Minicap library](https://github.com/openstf/minicap) when working with emulators instead of physical devices. 

EmuCapture has been tested on Ubuntu 14.04 and Python 2.7.8. Compatibility with other OSes and Python versions is unknown.

## Requirements
* Xvfb
* Imagemagick
* Android SDK
	- <sdk-path>/tools and <sdk_path>/platform-tools> need to be added to your PATH variable.
	- AVDs need to be created before using EmuCapture. If you want to run N concurrent emulators, there should be N separate AVDs.

## Features
* Uses Xvfb to start a display (with supplied display number) with a virtual framebuffer that is memory mapped to a file.
* Launches Android emulator on that display.
* Finds out dimension of window and uses Imagemagick to capture corresponding region from framebuffer and convert it to JPEG.
* Starts a TCP server that listens on port (6100 + display_number) for clients and once connected sends out a global header followed by a continous stream of JPEG frames (format in Usage section).

## Usage

### Running

```bash
usage: emucapture.py [-h] display_num avd_name

positional arguments:
  display_num  The display number to use with Xvfb
  avd_name     The name of the AVD instance to use

optional arguments:
  -h, --help   show this help message and exit
 ```
It takes upwards of five minutes for EmuCapture to launch the Emulator and be ready for clients. Once it is ready, you can connect to it using
```bash
nc localhost <portnumber>
```
The port number is computed from the display number. For example, if the display number is 3, the port number is 6103. If it is 4, port number is 6104 and so on. The default display number is 0 and other applications will have windows on it (you should not use it with EmuCapture).

We closely follow the [Minicap protocol](https://github.com/openstf/minicap)). When you first connect to the socket, you get a global header followed by the first frame. The global header will not appear again. More frames keep getting sent until you stop EmuCapture.

### Global header binary format

| Bytes | Length | Type | Explanation |
|-------|--------|------|-------------|
| 0     | 1 | unsigned char | Version (currently 1) |
| 1     | 1 | unsigned char | Size of the header (from byte 0) |
| 2-5   | 4 | uint32 (low endian) | Number to identify specific emulator instance when querying devices through ADB (eg. 5554) |
| 6-9   | 4 | uint32 (low endian) | Display width in pixels |
| 10-13 | 4 | uint32 (low endian) | Display height in pixels |
| 14-17 | 4 | uint32 (low endian) | Display width in pixels |
| 18-21 | 4 | uint32 (low endian) | Display height in pixels |
| 22    | 1 | unsigned char | Display orientation (fixed to 0) |
| 23    | 1 | unsigned char | Quirk bitflags (fixed to 1) |

#### Quirk bitflags

Minicap provided three Quirk bitflags to let the client know if Minicap was operating under certain conditions.
Currently, we always report QUIRK_DUMB as that condition is always true for EmuCapture:

| Value | Name | Explanation |
|-------|------|-------------|
| 1     | QUIRK_DUMB | Frames will get sent even if there are no changes from the previous frame. Informative, doesn't require any actions on your part. You can limit the capture rate by reading frame data slower in your own code if you wish. |

### Frame binary format

Appears a potentially unlimited number of times.

| Bytes | Length | Type | Explanation |
|-------|--------|------|-------------|
| 0-3   | 4 | uint32 (low endian) | Frame size in bytes (=n) |
| 4-(n+4) | n | unsigned char[] | Frame in JPG format |