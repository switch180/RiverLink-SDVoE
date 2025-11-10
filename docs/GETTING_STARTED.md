# 🚀 Getting Started with RiverLink SDVoE Matrix

This guide will walk you through setting up the RiverLink SDVoE Matrix integration for Home Assistant.

---

## 📋 Prerequisites

Before you begin, ensure you have the following:

### Required Hardware
- **SDVoE-compatible devices** (transmitters and receivers)
- **10GbE network switch** (SDVoE-certified recommended)
- **Windows PC** (Windows 10 or Windows 11) for running the BlueRiver Control Server

### Required Software
- **Home Assistant** 2025.2.4 or newer
- **BlueRiver Control Server** (included with IPA Manager software)

### Network Requirements
- All devices (SDVoE hardware, Windows PC, Home Assistant) must be on the same local network
- Default API port: 6970 (configurable)

---

## Step 1: Install BlueRiver Control Server

The BlueRiver Control Server is **required** for this integration to work. It acts as the API server that Home Assistant communicates with to control your SDVoE devices.

### Download IPA Manager

1. Visit the [WolfPack SDVoE product page](https://www.hdtvsupply.com/sdvoe-4k-60-1x2-hdmi-splitter-over-lan.html)
2. Click on the **"Software"** tab
3. Download the **IPA Manager** ZIP file
4. Extract the ZIP file to a location on your Windows PC

### Install IPA Manager

1. Navigate to the extracted folder
2. Run the **IPA Manager installer**
3. Follow the installation prompts
4. Complete the installation

### Launch IPA Manager

1. Open **IPA Manager** from your Start menu or desktop shortcut
2. The IPA Manager GUI will launch
3. When IPA Manager is running, it automatically starts the **blueriver_control** process on port 6970. You don't need to login, but if you choose to the default login is admin:admin.
4. This process runs in the background and provides the API that Home Assistant will connect to

### Important Notes

⚠️ **Keep IPA Manager Running**: The IPA Manager application (and its blueriver_control process) must remain running for Home Assistant to communicate with your SDVoE devices. It must be on the same network (subnet) as your SDVoE devices.

💡 **Tips**:
- Consider setting up a separate PC or VM to run IPA Manager in the background
- The Windows PC running IPA Manager can be any machine on the SDVoE network

---

## Step 2: Install RiverLink Integration in Home Assistant

You can install the RiverLink SDVoE Matrix integration using either HACS (recommended) or manual installation.

### Option A: HACS Installation (Recommended)

1. Open **HACS** in Home Assistant
2. Go to **"Integrations"**
3. Click the **three dots** in the top right corner
4. Select **"Custom repositories"**
5. Add `https://github.com/switch180/RiverLink-SDVoE` as an **Integration**
6. Click **"Install"**
7. **Restart Home Assistant**

### Option B: Manual Installation

1. Download the latest release from the [releases page](https://github.com/switch180/RiverLink-SDVoE/releases)
2. Extract the `riverlink` folder from the archive
3. Copy the `riverlink` folder to your `config/custom_components` directory
4. **Restart Home Assistant**

---

## Step 3: Configure the Integration

Once the integration is installed and Home Assistant has restarted:

1. Go to **Settings → Devices & Services**
2. Click **"+ Add Integration"**
3. Search for **"RiverLink SDVoE Matrix"**
4. Enter your SDVoE system details:
   - **Host**: IP address of the Windows PC running BlueRiver Control Server (e.g., `10.0.1.135`)
   - **Port**: API port (default: `6970`)
   - **API Version**: BlueRiver API version (default: `2.13.0.0`)
5. Click **Submit**

The integration will now discover all receivers and transmitters on your network and automatically create entities for them.

---

## Step 4: Using Your SDVoE System

### Entities Created

Once configured, the integration creates the following entities:

#### Per Receiver (9 entities)
- **Sensors** (6):
  - Temperature
  - Video Source
  - Audio Source
  - Video Signal
  - IP Address
  - Firmware Version
- **Binary Sensors** (3):
  - Online Status
  - Video Streaming
  - Audio Streaming
- **Selects** (3):
  - Video Source (switch inputs)
  - Display Mode
  - Resolution Preset

#### Per Transmitter (7 entities)
- **Sensors** (6):
  - Temperature
  - HDMI Stream
  - Audio Stream
  - Input Signal
  - IP Address
  - Firmware Version
- **Binary Sensors** (1):
  - Online Status

### Basic Usage

**Routing Video**:
1. Find your receiver's "Video Source" select entity
2. Choose the desired transmitter from the dropdown
3. Video will route instantly with zero latency

**Changing Display Modes**:
1. Find your receiver's "Display Mode" select entity
2. Choose from 5 available modes:
   - Genlock (zero-frame latency)
   - Genlock Scaling
   - Fast Switch
   - Fast Switch Stretch
   - Fast Switch Crop

**Adjusting Resolution**:
1. Find your receiver's "Resolution Preset" select entity
2. Choose from 26 named presets (broadcast + computer formats)
3. Resolution changes apply instantly


## 🆘 Need Help?

- **🐛 Report a bug**: [Open an issue](https://github.com/switch180/RiverLink-SDVoE/issues/new?template=bug.yml)
- **✨ Request a feature**: [Open an issue](https://github.com/switch180/RiverLink-SDVoE/issues/new?template=feature_request.yml)

---

## 🔄 Next Steps

- Explore the [README](../README.md) for feature details
- Read the [Contributing Guide](../CONTRIBUTING.md) if you'd like to contribute

---

**Congratulations!** You're now ready to control your SDVoE system with Home Assistant! 🎉
