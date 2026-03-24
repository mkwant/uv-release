import shutil
import subprocess
from typing import Annotated, Literal, Sequence

import typer

app = typer.Typer(help="Release tool: bump version, tag, and push.")

GIT_REMOTE_DEFAULT = "origin"


def run(cmd: Sequence[str], capture: bool = False) -> str:
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
        typer.secho(message=f"Command failed: {' '.join(cmd)}", fg=typer.colors.RED)
        if e.stdout:
            typer.echo(e.stdout)
        if e.stderr:
            typer.echo(e.stderr)
        raise typer.Exit(1)


def check_git_clean(force: bool) -> None:
    """Check if git is clean, i.e. there are no uncommitted changes."""
    has_head = (
        subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD"],  # noqa: S607
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode
        == 0
    )

    if not has_head:
        typer.secho(
            message="No commits yet — skipping git clean check.",
            fg=typer.colors.YELLOW,
        )
        return

    is_clean = (
        subprocess.run(["git", "diff-index", "--quiet", "HEAD", "--"]).returncode  # noqa: S607
        == 0
    )

    if is_clean:
        return

    if not force:
        typer.secho(
            message="Error: git is not clean. Commit your changes or use --force.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    typer.secho(
        message="Warning: git is dirty, continuing due to --force.",
        fg=typer.colors.YELLOW,
    )


def check_uv() -> None:
    """Check if uv is available."""
    if shutil.which("uv") is None:
        typer.secho(
            message="Error: uv is not installed. https://docs.astral.sh/uv/",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)


def has_remote(name: str = GIT_REMOTE_DEFAULT) -> bool:
    """Check if a remote is configured."""
    return (
        subprocess.run(  # noqa: S603
            ["git", "remote", "get-url", name],  # noqa: S607
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode
        == 0
    )


try:
    from uv_release import __version__
except ImportError:
    __version__ = "unknown"


def version_callback(value: bool):
    """Return the program version."""
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.command(no_args_is_help=True)
def release(
    version: Annotated[Literal["major", "minor", "patch"], typer.Argument(help="Version bump")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Force release even if git is dirty")] = False,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation")] = False,
    _show_version: Annotated[
        bool,
        typer.Option(
            "--version", "-v",
            callback=version_callback,
            is_eager=True,
            help="Show version and exit",
        ),
    ] = False,
) -> None:
    """Release the project and bump version."""
    check_git_clean(force)
    check_uv()

    typer.echo("🔍  Would bump version:")
    output = run(cmd=["uv", "version", "--bump", version, "--dry-run"], capture=True)
    typer.echo(output)

    if not (force or yes):
        confirm = typer.confirm("Do you want to release?")
        if not confirm:
            typer.echo("Aborted.")
            raise typer.Exit()

    # Apply version bump
    run(["uv", "version", "--bump", version])
    new_version = run(cmd=["uv", "version", "--short"], capture=True)
    typer.secho(message=f"📦 New version: {new_version}", fg=typer.colors.GREEN)

    # Git operations
    run(["git", "add", "pyproject.toml", "uv.lock"])
    try:
        run(["git", "commit", "-m", f"bump version to {new_version}"])
    except typer.Exit:
        typer.secho(message="Nothing to commit.", fg=typer.colors.YELLOW)

    run(["git", "tag", "-a", f"v{new_version}", "-m", f"v{new_version}"])

    if has_remote():
        typer.echo("🚀 Pushing changes and tags...")
        try:
            run(["git", "push", GIT_REMOTE_DEFAULT])
            run(["git", "push", GIT_REMOTE_DEFAULT, "--tags"])
        except typer.Exit:
            typer.secho(
                message="Pushing failed. Check your git remote settings.",
                fg=typer.colors.RED,
            )
            raise

    typer.secho(message="✅ Release complete!", fg=typer.colors.GREEN)


if __name__ == "__main__":
    app()
