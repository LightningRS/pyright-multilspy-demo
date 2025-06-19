#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import gzip
import io
import os
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

import loguru
import requests


def main(force_update=False):
    TGZ_URL = "https://github.com/microsoft/pyright/releases/latest/download/pyright.tgz"
    PYRIGHT_ROOT = Path(__file__).parent.parent / "third_party" / "pyright"
    logger = loguru.logger.bind(name="init_pyright")

    # Check Node.js executable
    path_env = os.environ.get('PATH', '')
    if '~' in path_env:
        path_env = path_env.replace('~', os.path.expanduser('~'))
    node_path = shutil.which('node', path=path_env)
    if not node_path:
        logger.error("Node.js executable not found!")
        exit(1)
    logger.info(f"node executable path: {node_path}")
    if not os.access(node_path, os.X_OK):
        logger.error(f"Node.js executable {node_path} is not executable!")
        exit(1)

    # Check Node.js version
    node_version = subprocess.check_output([node_path, '-v']).decode('utf-8').strip()
    logger.info(f"Node.js version: {node_version}")

    # Check and download pyright
    if not Path(PYRIGHT_ROOT / "package" / "langserver.index.js").exists() or force_update:
        if Path(PYRIGHT_ROOT / "package").exists():
            shutil.rmtree(PYRIGHT_ROOT / "package")
        logger.info(f"Downloading pyright from: {TGZ_URL}")
        try:
            response = requests.get(TGZ_URL)
            tgz_raw = response.content
            with gzip.open(io.BytesIO(tgz_raw), "rb") as f:
                with tarfile.open(fileobj=f) as tar:
                    tar.extractall(PYRIGHT_ROOT, filter='data')
            logger.info("Downloaded pyright.")
        except Exception as e:
            logger.error(e)
            logger.error(
                f"Failed to download pyright! "
                f"Please download pyright manually from {TGZ_URL} "
                f"and decompress it into {PYRIGHT_ROOT}."
            )
    else:
        logger.info("pyright already exists.")


if __name__ == "__main__":
    main(force_update='-f' in sys.argv or '--force' in sys.argv)
