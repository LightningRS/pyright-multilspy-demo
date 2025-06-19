#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import json
from pathlib import Path

import richuru
from loguru import logger
from multilspy.multilspy_config import MultilspyConfig
from rich.console import Console

from pyright_server import PyRightServer, MultilspyLoguruLogger

console = Console()
richuru.install(rich_console=console, level='DEBUG')


async def main():
    proj_root = Path(__file__).parent.parent
    test_root = proj_root / "testRoot"
    python_path = proj_root / ".venv/bin/python"

    config = MultilspyConfig.from_dict(
        {
            "code_language": "python",
            "trace_lsp_communication": True,
        }
    )
    m_logger = MultilspyLoguruLogger()

    # Create our own LanguageServer, since default LanguageServer does not support pyright.
    lsp = PyRightServer(
        config=config,
        logger=m_logger,
        repository_root_path=str(test_root),
        # For demo: use our virtual environment as python path
        python_path=python_path,
    )
    async with lsp.start_server():
        logger.info("Requesting definition of G_VAR in demo1.py...")
        demo1_path = test_root / 'demo1.py'
        with lsp.open_file(relative_file_path='demo1.py'):
            res = await lsp.request_definition(
                relative_file_path='demo1.py',
                line=14,
                column=14,
            )
            
            # For demo only: generate position string for easier debug.
            for r_def in res:
                if 'range' in r_def:
                    range_str = f"{r_def['range']['start']['line'] + 1}:{r_def['range']['start']['character'] + 1}"
                    r_def['pos'] = f"{r_def['absolutePath']}:{range_str}"  # type: ignore
            
            # Output demo result.
            logger.info("G_VAR definitions:\n" + json.dumps(res, indent=2, ensure_ascii=False))

            res = await lsp.request_document_symbols(relative_file_path='demo1.py')
            logger.info("Document symbols:\n" + json.dumps(res, indent=2, ensure_ascii=False))

            res = await lsp.server.send_request(
                method='textDocument/semanticTokens/full',
                params={
                    'textDocument': {
                        "uri": demo1_path.as_uri(),
                    }
                }
            )
            logger.info("Semantic tokens:\n" + json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
