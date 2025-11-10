# 🎬 RiverLink SDVoE Matrix

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

[![hacs][hacsbadge]][hacs]

_Home Assistant custom integration for SDVoE API™ control._

**⚠️ This integration is currently under active development.**

---

## 📖 About

**RiverLink SDVoE Matrix** is a Home Assistant custom integration that enables control of **SDVoE™ (Software Defined Video over Ethernet)** matrix systems via the SDVoE API™. This integration allows you to manage video routing, audio routing, and display modes directly from your Home Assistant dashboard.

### 🔌 Requirements

- **Home Assistant** 2025.2.4 or newer
- **BlueRiver® AVP devices** with network-accessible API endpoint
- **SDVoE API server** running on your network (default port: 6970)
  - Most users: Install IPA Manager - [Setup guide](docs/GETTING_STARTED.md#step-1-install-blueriver-control-server)
  - Advanced users: Bring your own BlueRiver Control Server implementation
- **SDVoE API™** version 2.13.0.0 or newer

**Developer:** [switch180](https://github.com/switch180)

---

## ✨ Features

### 🎯 Core Functionality
- ✅ **Device Discovery** - Automatic detection of receivers and transmitters
- ✅ **Video Routing** - Dynamic source-to-display mapping via HDMI streams
- ✅ **Audio Routing** - HDMI embedded audio follows video routing
- ✅ **Temperature Monitoring** - Real-time device temperature sensors
- ✅ **Connection Status** - Online/offline state for all devices
- ✅ **Stream State Tracking** - Monitor active/inactive video streams

### 🖥️ Display Control
- ✅ **Display Modes** - Full support for all 5 modes:
  - **Genlock** (zero-frame latency passthrough)
  - **Genlock Scaling** (low-latency with resolution conversion)
  - **Fast Switch** (multi-source switching, aspect-preserved)
  - **Fast Switch Stretch** (multi-source, stretch to fill)
  - **Fast Switch Crop** (multi-source, crop to fit)
- ✅ **Resolution Presets** - 26 named presets (broadcast + computer formats)
- ✅ **Custom Resolutions** - Support for non-standard resolutions via genlock mode
- ✅ **Signal Information** - Resolution, color space, HDCP status, bit depth

### 📊 Entity Types Created
- **Per Receiver** (9 entities):
  - 6 Sensors: Temperature, Video Source, Audio Source, Video Signal, IP Address, Firmware
  - 3 Binary Sensors: Online, Video Streaming, Audio Streaming
  - 3 Selects: Video Source, Display Mode, Resolution Preset

- **Per Transmitter** (7 entities):
  - 6 Sensors: Temperature, HDMI Stream, Audio Stream, Input Signal, IP Address, Firmware
  - 1 Binary Sensor: Online

### 🚧 Not Yet Implemented
- ⏳ **Multiview/PIP** - Picture-in-picture and multiview displays
- ⏳ **Videowall APIs** - Synchronized multi-display configurations
- ⏳ **Service Calls** - Advanced automation via Home Assistant services
- ⏳ **Audio-Only Routing** - Independent audio matrix functionality

---

## 🚀 Quick Start

> **⚠️ Important:** Before installing the integration, you must set up the BlueRiver Control Server (or bring your own SDVoE API server). This is required for the integration to communicate with your SDVoE devices.

1. **Set up BlueRiver Control Server** - [Step-by-step guide](docs/GETTING_STARTED.md#step-1-install-blueriver-control-server)
2. **Install the Integration** - [Installation instructions](docs/GETTING_STARTED.md#step-2-install-riverlink-integration-in-home-assistant)
3. **Configure in Home Assistant** - [Configuration guide](docs/GETTING_STARTED.md#step-3-configure-the-integration)
4. **Start Using SDVoE** - [Usage examples](docs/GETTING_STARTED.md#step-4-using-your-sdvoe-system)

📖 **[Read the complete Getting Started Guide →](docs/GETTING_STARTED.md)**

---

## 🤝 Contributing

Contributions are welcome! Please read the [Contributing Guide](CONTRIBUTING.md) for:
- Development environment setup
- Code of conduct
- Development workflow
- Pull request process
- Coding standards

---

## ⚖️ License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

---

## 🆘 Support

- **🐛 Report a bug**: [Open an issue](https://github.com/switch180/RiverLink-SDVoE/issues/new?template=bug.yml)
- **✨ Request a feature**: [Open an issue](https://github.com/switch180/RiverLink-SDVoE/issues/new?template=feature_request.yml)
- **📖 Documentation**: [Getting Started Guide](docs/GETTING_STARTED.md)

---

## 🧾 Trademarks, Legal & Disclaimer

### ⚠️ Non-Affiliation Notice

**This project is an independent open-source integration developed by the community.** RiverLink SDVoE Matrix is **NOT** affiliated with, endorsed by, sponsored by, or officially connected to the SDVoE Alliance®, Semtech Corporation®, or any other trademark holder mentioned in this documentation. This integration does not contain any properitary code of the aforementioned organizations.

This integration is designed purely for interoperability with SDVoE™ technology and the SDVoE API™. We respect all intellectual property rights and make no claims to ownership of any third-party trademarks, service marks, or proprietary technologies referenced herein. The development of this integration is an independent effort to enable Home Assistant users to control their SDVoE™-compatible devices.

### Trademark Acknowledgments

- **SDVoE™**, **SDVoE API™**, and **SDVoE Alliance®** are trademarks of the SDVoE Alliance.
- **BlueRiver®** and **Semtech®** are registered trademarks of Semtech Corporation or its affiliates.

All other trademarks, service marks, and trade names referenced in this project are the property of their respective owners.

### Copyright & Licensing

This project is licensed under the **MIT License** and implements interoperability with the SDVoE API™. The integration does **not** redistribute any proprietary content, firmware, or copyrighted materials from third parties. All API specifications, protocols, and documentation are the property of their respective owners and are used solely for the purpose of enabling interoperability.

---

[commits-shield]: https://img.shields.io/github/commit-activity/y/switch180/RiverLink-SDVoE.svg?style=for-the-badge
[commits]: https://github.com/switch180/RiverLink-SDVoE/commits/main
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[license-shield]: https://img.shields.io/github/license/switch180/RiverLink-SDVoE.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/switch180/RiverLink-SDVoE.svg?style=for-the-badge
[releases]: https://github.com/switch180/RiverLink-SDVoE/releases
