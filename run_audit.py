#!/usr/bin/env python3
"""
Entry point. Run this file to execute a full structured data audit.

Usage:
    python run_audit.py
"""

from audit_tool.auditor import run

if __name__ == "__main__":
    run(config_path="config.yaml", output_dir="reports")
