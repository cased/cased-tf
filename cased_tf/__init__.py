#!/usr/bin/env python3
import click
import json
import subprocess
import requests
import os
import yaml
from typing import Optional, Dict, Any


def load_config(config_file: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration from config file"""
    if not config_file:
        # Check default locations
        default_locations = [
            os.path.expanduser("~/.config/cased/config.yml"),
            os.path.expanduser("~/.cased/config.yml"),
            ".cased.yml",
        ]
        for loc in default_locations:
            if os.path.exists(loc):
                click.echo(f"Found config file: {loc}")
                config_file = loc
                break

    if not config_file or not os.path.exists(config_file):
        click.echo("No config file found")
        return {}

    try:
        with open(config_file) as f:
            config = yaml.safe_load(f) or {}
            click.echo(f"Loaded config: {json.dumps(config, indent=2)}")
            return config
    except Exception as e:
        raise click.UsageError(f"Failed to load config file: {e}")


class TerraformAnalyzer:
    def __init__(self, working_dir: Optional[str] = None):
        self.working_dir = working_dir or os.getcwd()

    def validate_terraform_directory(self) -> None:
        """Check if directory contains terraform files"""
        tf_files = [f for f in os.listdir(self.working_dir) if f.endswith(".tf")]
        if not tf_files:
            raise click.UsageError(
                f"No .tf files found in {self.working_dir}. "
                "Please run this command from a directory containing Terraform files "
                "or specify --working-dir"
            )

        # Check if terraform is initialized
        if not os.path.exists(os.path.join(self.working_dir, ".terraform")):
            raise click.UsageError("Terraform not initialized. Please run 'terraform init' first.")

    def get_show_output(self) -> Dict[str, Any]:
        """Run terraform show -json and return parsed output"""
        self.validate_terraform_directory()

        result = subprocess.run(
            ["terraform", "show", "-json"],
            capture_output=True,
            text=True,
            cwd=self.working_dir,
        )

        if result.returncode != 0:
            raise click.UsageError(f"terraform show failed:\n{result.stderr}")

        try:
            output = json.loads(result.stdout)
            click.echo("\nTerraform output summary:")
            if "values" in output:
                click.echo("- Found values section")
                if "root_module" in output["values"]:

                    def print_module_resources(module_data: Dict[str, Any], prefix: str = ""):
                        resources = module_data.get("resources", [])
                        click.echo(f"{prefix}- Found {len(resources)} resources in module")
                        for r in resources:
                            if r.get("type", "").startswith("aws_"):
                                click.echo(
                                    f"{prefix}  - {r['type']}: {r.get('name')} "
                                    f"({r.get('values', {}).get('id', 'no id')})"
                                )

                        # Process child modules
                        for child in module_data.get("child_modules", []):
                            click.echo(f"{prefix}- Child module: {child.get('address', 'unknown')}")
                            print_module_resources(child, prefix + "  ")

                    print_module_resources(output["values"]["root_module"])
            return output
        except json.JSONDecodeError:
            raise click.UsageError(
                "Failed to parse terraform show output as JSON. "
                f"Output: {result.stdout[:200]}..."
            )


class CasedAPI:
    def __init__(self, api_key: str, base_url: str = "https://app.cased.com"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/").replace("/api/v1", "")

    def analyze_terraform(
        self,
        project: str,
        environment: str,
        show_output: Dict[str, Any],
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Send terraform output to Cased API for analysis"""
        url = f"{self.base_url}/api/v1/projects/{project}/infra/local"
        payload = {
            "terraform_show_output": show_output,
            "environment": environment,
        }

        if dry_run:
            click.secho("\n=== Dry Run - API Request Details ===\n", fg="yellow")
            click.echo(f"URL: {url}")
            click.echo("\nHeaders:")
            click.echo("  Authorization: Bearer [REDACTED]")
            click.echo("  Content-Type: application/json")
            click.echo("\nPayload:")
            click.echo(json.dumps(payload, indent=2))
            click.echo("\nNo API call will be made in dry-run mode.")
            return {}

        response = requests.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
        )
        response.raise_for_status()
        return response.json()


def print_drift_report(report: Dict[str, Any]) -> None:
    """Pretty print the drift analysis report"""
    if not report:  # Empty in case of dry run
        return

    click.echo("\n=== Infrastructure Drift Report ===\n")

    all_resources = (
        report.get("managed_resources", [])
        + report.get("unmanaged_resources", [])
        + report.get("missing_resources", [])
    )

    if not all_resources:
        click.secho("✅ No resources found", fg="green", bold=True)
        return

    # Print managed resources
    managed = report.get("managed_resources", [])
    if managed:
        click.secho("\n🔍 Managed Resources:", fg="blue", bold=True)
        for resource in managed:
            status_color = "green" if resource["status"] == "synced" else "yellow"
            click.secho(
                f"• {resource['service_name']} - {resource['name']} ({resource['id']})",
                fg=status_color,
            )
            click.echo(f"  Type: {resource['service_type']}")
            click.echo(f"  Status: {resource['status']}")
            if resource.get("drift"):
                click.secho("  Changes:", fg="yellow")
                for change in resource["drift"]:
                    click.echo(
                        f"    - {change['field']}: expected {change['expected']}, "
                        f"got {change['actual']}"
                    )
            click.echo()

    # Print unmanaged resources
    unmanaged = report.get("unmanaged_resources", [])
    if unmanaged:
        click.secho("\n⚠️  Unmanaged Resources:", fg="yellow", bold=True)
        for resource in unmanaged:
            click.secho(
                f"• {resource['service_name']} - {resource['name']} ({resource['id']})",
                fg="yellow",
            )
            click.echo(f"  Type: {resource['service_type']}")
            click.echo()

    # Print missing resources
    missing = report.get("missing_resources", [])
    if missing:
        click.secho("\n❌ Missing Resources:", fg="red", bold=True)
        for resource in missing:
            click.secho(
                f"• {resource['service_name']} - {resource['name']} ({resource['id']})",
                fg="red",
            )
            click.echo(f"  Type: {resource['service_type']}")
            click.echo()


@click.group()
def cli():
    """Cased Terraform Analysis Tool"""
    pass


@cli.command()
@click.option(
    "--project",
    required=False,  # Not required if in config
    help="Project name (org/project)",
)
@click.option(
    "--environment",
    required=False,  # Not required if in config
    help="Environment name (e.g. prod, staging)",
)
@click.option(
    "--api-key",
    envvar="CASED_API_KEY",
    required=False,  # Not required for dry run
    help="Cased API key (or set CASED_API_KEY env var)",
)
@click.option(
    "--api-url",
    envvar="CASED_API_URL",
    default="https://app.cased.com",
    help="Cased API URL (or set CASED_API_URL env var)",
)
@click.option(
    "--working-dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    help="Terraform working directory",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be sent to the API without making the request",
)
@click.option(
    "--config",
    type=click.Path(exists=True, dir_okay=False),
    help="Path to config file",
)
@click.option(
    "--local",
    is_flag=True,
    help="Use local development server (http://localhost:3000)",
)
def analyze(
    project: Optional[str],
    environment: Optional[str],
    api_key: Optional[str],
    api_url: str,
    working_dir: Optional[str],
    dry_run: bool,
    config: Optional[str],
    local: bool,
):
    """Analyze Terraform configuration for drift"""
    try:
        # Load config file
        cfg = load_config(config)

        # Config precedence: CLI args > env vars > config file
        if not api_key:
            api_key = os.getenv("CASED_API_KEY") or cfg.get("api_key")

        if local:
            api_url = "http://localhost:3000"
        elif api_url == "https://app.cased.com":  # Only override default
            api_url = os.getenv("CASED_API_URL") or cfg.get("api_url", api_url)

        project = project or cfg.get("project")
        if not project:
            raise click.UsageError("Project must be specified via --project or config file")

        environment = environment or cfg.get("environment")
        if not environment:
            raise click.UsageError("Environment must be specified via --environment or config file")

        if not working_dir and cfg.get("working_dir"):
            working_dir = os.path.expanduser(cfg.get("working_dir"))

        # Initialize analyzer and API client
        analyzer = TerraformAnalyzer(working_dir)

        # Only require API key if not doing a dry run
        if not dry_run and not api_key:
            raise click.UsageError("--api-key is required unless using --dry-run")

        api = CasedAPI(api_key or "dry-run-key", api_url)

        click.echo("Running terraform show...")
        show_output = analyzer.get_show_output()

        if dry_run:
            click.secho("\nDry run mode - showing what would be analyzed:", fg="yellow")
        else:
            click.echo("\nAnalyzing infrastructure...")

        report = api.analyze_terraform(
            project=project,
            environment=environment,
            show_output=show_output,
            dry_run=dry_run,
        )

        print_drift_report(report)

    except subprocess.CalledProcessError as e:
        click.secho(f"\nError running terraform command: {e}", fg="red")
        click.echo(f"Output: {e.output.decode() if e.output else 'No output'}")
        raise click.Abort()
    except requests.RequestException as e:
        click.secho(f"\nError calling Cased API: {e}", fg="red")
        raise click.Abort()
    except Exception as e:
        click.secho(f"\nUnexpected error: {e}", fg="red")
        raise click.Abort()


if __name__ == "__main__":
    cli()
