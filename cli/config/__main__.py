"""Allow running the config package as: python -m config.wizard"""

from cli.config.wizard import run_wizard

if __name__ == "__main__":
    run_wizard()
