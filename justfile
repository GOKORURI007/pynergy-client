set shell := ["pwsh", "-c"]

scripts_dir := "scripts"

default:
  @just --list

format:
    uv run {{scripts_dir}}/format.py

test:
    uv run {{scripts_dir}}/test_all.py

release:
    uv run {{scripts_dir}}/release.py
