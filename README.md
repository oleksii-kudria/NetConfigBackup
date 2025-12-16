# NetConfigBackup

Baseline project structure for backing up Cisco and MikroTik network device configurations.

## Project layout
- `scripts/run.py`: Entry point for the command-line interface.
- `src/app`: Application package split into core utilities and vendor-specific helpers.
- `config/`: Sample inventory and secrets templates (copy to `config/*.yml` before use).
- `backups/`: Default output directory for configuration archives.

## Getting started
1. Create a virtual environment and install dependencies:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Copy the example configuration files and fill in real values:
   ```bash
   cp config/devices.yml.example config/devices.yml
   cp config/secrets.yml.example config/secrets.yml
   ```
3. View available commands:
   ```bash
   python3 scripts/run.py --help
   ```
