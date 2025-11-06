# RiverLink SDVoE Matrix

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

[![hacs][hacsbadge]][hacs]

_Integration to control RiverLink SDVoE Matrix systems with Home Assistant._

**This integration is currently under development.**

## About

RiverLink SDVoE Matrix is a Home Assistant custom integration for controlling SDVoE (Software Defined Video over Ethernet) matrix systems. This integration allows you to manage video routing and control matrix operations directly from Home Assistant.

**Developer:** [switch180](https://github.com/switch180)

## Features

- Control SDVoE matrix video routing
- Monitor device connectivity
- Manage video stream assignments
- Raw socket communication with matrix controller

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add `https://github.com/switch180/RiverLink-SDVoE` as an Integration
6. Click "Install"
7. Restart Home Assistant

### Manual Installation

1. Download the latest release from the [releases page](https://github.com/switch180/RiverLink-SDVoE/releases)
2. Extract the `riverlink` folder from the archive
3. Copy the `riverlink` folder to your `custom_components` directory
4. Restart Home Assistant

## Configuration

1. Go to Settings → Devices & Services
2. Click "+ Add Integration"
3. Search for "RiverLink SDVoE Matrix"
4. Follow the configuration steps

## Development

For development and testing, you can use the included devcontainer:

1. Open this repository in Visual Studio Code
2. When prompted, reopen in container
3. Run `scripts/develop` to start Home Assistant with the integration loaded

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the terms of the LICENSE file included in this repository.

## Support

- [Report a bug](https://github.com/switch180/RiverLink-SDVoE/issues)
- [Request a feature](https://github.com/switch180/RiverLink-SDVoE/issues)

---

[commits-shield]: https://img.shields.io/github/commit-activity/y/switch180/RiverLink-SDVoE.svg?style=for-the-badge
[commits]: https://github.com/switch180/RiverLink-SDVoE/commits/main
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[license-shield]: https://img.shields.io/github/license/switch180/RiverLink-SDVoE.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/switch180/RiverLink-SDVoE.svg?style=for-the-badge
[releases]: https://github.com/switch180/RiverLink-SDVoE/releases
