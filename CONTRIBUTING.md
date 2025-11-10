# 🤝 Contribution Guidelines

Contributing to this project should be as easy and transparent as possible, whether it's:

- 🐛 Reporting a bug
- 💬 Discussing the current state of the code
- 🔧 Submitting a fix
- ✨ Proposing new features

---

## GitHub is Used for Everything

GitHub® is used to host code, to track issues and feature requests, as well as accept pull requests.

Pull requests are the best way to propose changes to the codebase.

1. **Fork the repo** and create your branch from `main`.
2. If you've **changed something**, update the documentation.
3. Make sure your **code lints** (using `scripts/lint`).
4. **Test your contribution** thoroughly.
5. **Issue that pull request!**

---

## 📜 Any Contributions You Make Will Be Under the MIT Software License

In short, when you submit code changes, your submissions are understood to be under the same [MIT License](http://choosealicense.com/licenses/mit/) that covers the project. Feel free to contact the maintainers if that's a concern.

---

## 🐛 Report Bugs Using GitHub's [Issues](../../issues)

GitHub® issues are used to track public bugs.  
Report a bug by [opening a new issue](../../issues/new/choose); it's that easy!

---

## ✍️ Write Bug Reports with Detail, Background, and Sample Code

**Great Bug Reports** tend to have:

- A quick summary and/or background
- Steps to reproduce
  - Be specific!
  - Give sample code if you can.
- What you expected would happen
- What actually happens
- Notes (possibly including why you think this might be happening, or stuff you tried that didn't work)

People *love* thorough bug reports. I'm not even kidding.

---

## 🎨 Use a Consistent Coding Style

This project uses **[Ruff](https://github.com/astral-sh/ruff)** for linting and code formatting.

### Running the Linter

```bash
scripts/lint
```

Ruff will automatically check code style, formatting, and common issues. Make sure your code passes all checks before submitting a pull request.

---

## 🧪 Test Your Code Modifications

### Prerequisites

Before you can develop for this integration, you need:
- **BlueRiver Control Server** running on your network - [Setup instructions](docs/GETTING_STARTED.md#step-1-install-blueriver-control-server)
- **Visual Studio Code** with Remote Containers extension
- **Docker** installed and running

### Development Environment

This project uses a **VS Code devcontainer** for development:

1. Open this repository in **Visual Studio Code**
2. When prompted, click **"Reopen in Container"**
3. Run `scripts/setup` to install dependencies
4. Run `scripts/develop` to start Home Assistant with the integration loaded

The devcontainer includes:
- Python 3.13
- Home Assistant 2025.2.4
- Ruff (linting/formatting)
- Pre-configured debugging

With this container you will have a standalone Home Assistant instance running and already configured with the included [`configuration.yaml`](./config/configuration.yaml) file.

### Development Commands

**Install dependencies:**
```bash
scripts/setup
```

**Start Home Assistant with integration:**
```bash
scripts/develop
```

**Run linting:**
```bash
scripts/lint
```

### Testing Your Changes

1. Make your code changes in the `custom_components/riverlink/` directory
2. The devcontainer will automatically reload the integration
3. Configure the integration in Home Assistant pointing to your BlueRiver Control Server
4. Test your changes with real SDVoE devices or mocked data
5. Ensure all linting checks pass before submitting

---




## 🔒 Proprietary Content & Trade Secrets

**By submitting a contribution, you assert that:**

1. Your code is **original work** or properly licensed open-source code
2. Your contribution does **NOT** contain:
   - Proprietary code from any corporation or third party
   - Trade secrets or confidential information
   - Reverse-engineered code from closed-source products
   - Undocumented or private APIs
   - Any copyrighted material without proper licensing

3. Your contribution is submitted under the **MIT License**
4. You have the legal right to submit this contribution

**We cannot accept:**
- Decompiled or reverse-engineered firmware code
- Private/internal API implementations not publicly documented
- Any corporate "work product" to which you do not hold rights

All contributions must be based on **publicly available documentation** and **publicly documented APIs** only.

---

## ⚖️ License

By contributing, you agree that your contributions will be licensed under the **MIT License**.

---

## 🙏 Thank You!

Your contributions make this project better for everyone. We appreciate your time and effort in helping improve RiverLink SDVoE Matrix!

---

### Trademark Acknowledgments

- **SDVoE™**, **SDVoE API™**, and **SDVoE Alliance®** are trademarks of the SDVoE Alliance.
- **BlueRiver®** and **Semtech®** are registered trademarks of Semtech Corporation or its affiliates.

All other trademarks are the property of their respective owners.
