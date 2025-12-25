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

## Devices inventory schema
`config/devices.yml` stores every device in a single `devices` list and does **not**
contain passwords. Secrets are pulled via `auth.secret_ref` from `config/secrets.yml`.

Each device entry uses the following fields:
- `name` *(string, required)*: Unique identifier used in logs and backup paths.
- `vendor` *(required)*: Either `cisco` or `mikrotik`.
- `model` *(string, required)*: Device model for metadata.
- `host` *(string, required)*: IP address or DNS name.
- `port` *(integer, optional)*: SSH port, defaults to `22`.
- `username` *(string, required)*: Login user.
- `auth.secret_ref` *(string, required)*: Key that matches a device entry in `secrets.yml`.
- `backup.type` *(required)*: `running-config` for Cisco devices or `export` for MikroTik devices.

Refer to `config/devices.yml.example` for a complete, non-sensitive example.
