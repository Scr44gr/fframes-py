# Codec licenses

[Index](index.md) · [Encoding settings](rendering.md#encoding)

| Component | License |
| --- | --- |
| fframes-py | [MIT](../LICENSE) |
| FFmpeg | [LGPL](https://ffmpeg.org/legal.html) |
| OpenH264 | [BSD-2-Clause](../licenses/OpenH264.txt) |

Redistributing wheels must preserve third-party notices and satisfy FFmpeg's
LGPL requirements, including those for static linking. Custom FFmpeg builds
using libx264 add GPL obligations; libx264 is not bundled in the standard wheels.

H.264 patent licensing is separate. [Cisco's royalty coverage](https://www.openh264.org/faq.html)
does not automatically cover OpenH264 rebuilt or bundled in these wheels;
distribution and use may require a separate patent assessment.
