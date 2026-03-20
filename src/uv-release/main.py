import subprocess
from typing import Annotated, Literal

import typer

app = typer.Typer(help="Release tool: bump version, tag, and push.")


def run(cmd: list[str], capture: bool = False) -> str:
    """Run a command and optionally capture output."""
    try:
        result = subprocess.run(
            args=cmd,
            check=True,
            text=True,
            capture_output=capture,
        )
        return result.stdout.strip() if capture else ""
    except subprocess.CalledProcessError as e:
        typer.secho(f"Command failed: {' '.join(cmd)}", fg=typer.colors.RED)
        if e.stdout:
            typer.echo(e.stdout)
        if e.stderr:
            typer.echo(e.stderr)
        raise typer.Exit(1)


def check_git_clean(force: bool) -> None:
    try:
        subprocess.run(
            ["git", "diff-index", "--quiet", "HEAD", "--"],
            check=True,
        )
    except subprocess.CalledProcessError:
        if not force:
            typer.secho(
                "Error: git is not clean. Commit your changes or use --force.",
                fg=typer.colors.RED,
            )
            raise typer.Exit(1)
        typer.secho("Warning: git is dirty, continuing due to --force.", fg=typer.colors.YELLOW)


def check_uv() -> None:
    try:
        subprocess.run(
            args=["uv", "--version"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        typer.secho(
            "Error: uv is not installed. https://docs.astral.sh/uv/",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)


@app.command(no_args_is_help=True)
def release(
        version: Annotated[Literal['major', 'minor', 'patch'], typer.Argument(help="Version bump")],
        force: Annotated[bool, typer.Option("--force", "-f", help="Force release even if git is dirty")] = False,
) -> None:
    """Release the project and bump version."""
    check_git_clean(force)
    check_uv()

    typer.echo("🔍 Would bump version:")
    output = run(["uv", "version", "--bump", version, "--dry-run"], capture=True)
    typer.echo(output)

    if not force:
        confirm = typer.confirm("Do you want to release?")
        if not confirm:
            typer.echo("Aborted.")
            raise typer.Exit()

    # Apply version bump
    run(["uv", "version", "--bump", version])

    new_version = run(["uv", "version", "--short"], capture=True)
    typer.secho(f"📦 New version: {new_version}", fg=typer.colors.GREEN)

    # Git operations
    run(["git", "add", "pyproject.toml", "uv.lock"])
    run(["git", "commit", "-m", f"bump version to {new_version}"])
    run(["git", "tag", "-a", f"v{new_version}", "-m", f"v{new_version}"])

    typer.echo("🚀 Pushing changes...")
    run(["git", "push", "origin", "main"])
    run(["git", "push", "origin", f"v{new_version}"])

    typer.secho("✅ Release complete!", fg=typer.colors.GREEN)


if __name__ == "__main__":
    app()
