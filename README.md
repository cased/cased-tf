# Cased Terraform Analysis Tool

A CLI tool for analyzing Terraform configuration drift without sharing state files.

## Installation

There are two ways to install cased-tf:

### Option 1: Install directly from repository
```bash
# Install for current user (recommended)
pip install --user git+https://github.com/cased/cased-tf.git

# Or install system-wide (requires sudo)
sudo pip install git+https://github.com/cased/cased-tf.git
```

### Option 2: Install from cloned repository
```bash
# Clone the repository
git clone https://github.com/cased/cased-tf.git
cd cased-tf

# Install for current user (recommended)
pip install --user .

# Or install system-wide (requires sudo)
sudo pip install .
```

After installation, the `cased-tf` command will be available in your terminal. If you installed with `--user`, make sure your user's bin directory is in your PATH.

## Usage

```bash
# Set your API key (get this from Cased dashboard)
export CASED_API_KEY=your-api-key

# Run drift analysis in your Terraform directory
cd /path/to/terraform
cased-tf analyze --project cased/infra --environment prod --api-key your-api-key

# For more options
cased-tf analyze --help
```

### Options

- `--project <org/project>`: Project name (e.g. cased/infra)
- `--environment <name>`: Environment name (e.g. prod, staging)
- `--api-key <key>`: Cased API key (or set CASED_API_KEY env var)
- `--working-dir <path>`: Terraform working directory (defaults to current directory)
- `--dry-run`: Show what would be sent to the API without making the request
- `--config <path>`: Path to config file

## Requirements

- Python 3.7+
- Terraform 0.12+
- Cased API key

## Working Directory Requirements

The tool needs to run in a directory containing your Terraform configuration (where you would normally run `terraform plan`). The directory must:
- Contain `.tf` files
- Be initialized (`terraform init`)
- Have any required variables or backend configuration set up

## Detailed Usage

### Basic Analysis
```bash
# Go to your Terraform directory
cd /path/to/terraform

# Run analysis
cased-tf analyze --project cased/infra --environment prod
```

### Advanced Options
```bash
# Analyze a different directory
cased-tf analyze --project cased/infra --environment prod --working-dir /other/terraform/dir

# Use a different API endpoint
cased-tf analyze --project cased/infra --environment prod --api-url https://your-cased-instance

# Get help
cased-tf --help
cased-tf analyze --help
```

### Environment Variables

- `CASED_API_KEY`: Your Cased API key (required)
- `CASED_API_URL`: Custom API URL (optional, defaults to https://app.cased.com)

## Config File

You can store common settings in a YAML config file. The tool will look for config in these locations (in order):
1. `~/.config/cased/config.yml`
2. `~/.cased/config.yml`
3. `.cased.yml` (in current directory)

Or specify a custom location with `--config`:

```yaml
# ~/.cased/config.yml
api_key: your-api-key
api_url: https://app.cased.com  # or http://localhost:3000 for local development
project: your-org/project
environment: prod
working_dir: ~/terraform/configs
```

Config precedence: CLI args > environment variables > config file

## Local Development

For local development, you can either:
1. Use the `--local` flag to connect to http://localhost:3000
2. Set a custom URL via `--api-url` or config file

```bash
# Using --local flag
cased-tf analyze --project your-org/project --environment prod --local

# Or custom URL
cased-tf analyze --project your-org/project --environment prod --api-url http://localhost:3000
```

## How it Works

1. The tool runs these commands locally:
   - `terraform show -json`: Gets current state
   - `terraform plan -json`: Detects planned changes

2. It sends the JSON output to Cased for analysis

3. Cased compares your Terraform configuration with actual cloud resources

4. Results show:
   - Resources that have drifted
   - Unmanaged resources (in cloud but not in Terraform)
   - Missing resources (in Terraform but not in cloud)

No sensitive data or state files are shared - only the JSON output from Terraform commands.

## Getting Help

- Run `cased-tf --help` for command help
- Visit [docs.cased.com](https://docs.cased.com) for documentation
- Contact support@cased.com for assistance

## Development

For local development:

```bash
# Clone the repository
git clone https://github.com/cased/cli
cd cli

# Install in editable mode
pip install -e .
