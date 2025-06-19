#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
from contextlib import asynccontextmanager
import json
import logging
from pathlib import Path

from multilspy import LanguageServer
import richuru
from loguru import logger
from multilspy.multilspy_config import MultilspyConfig
from multilspy.language_servers.jedi_language_server.jedi_server import JediServer
from rich.console import Console

from pyright_server import PyRightServer, MultilspyLoguruLogger

console = Console()
richuru.install(rich_console=console, level='DEBUG')

@asynccontextmanager
async def start_pyright(
        src_root: Path,
        python_path: Path,
):
    config = MultilspyConfig.from_dict(
        {
            "code_language": "python",
            "trace_lsp_communication": True,
        }
    )
    m_logger = MultilspyLoguruLogger(name='PyrightLogger')

    # Create our own LanguageServer, since default LanguageServer does not support pyright.
    lsp = PyRightServer(
        config=config,
        logger=m_logger,
        repository_root_path=str(src_root),
        # For demo: use our virtual environment as python path
        python_path=python_path,
    )
    async with lsp.start_server():
        yield lsp


@asynccontextmanager
async def start_jedi(src_root: Path):
    config = MultilspyConfig.from_dict(
        {
            "code_language": "python",
            "trace_lsp_communication": True,
        }
    )
    m_logger = MultilspyLoguruLogger(name='JediLogger')
    lsp: JediServer = LanguageServer.create(config=config, logger=m_logger, repository_root_path=str(src_root)) # type: ignore

    if config.trace_lsp_communication:
        # Dump JSON string when tracing lsp communication.
        def logging_fn(source, target, msg):
            msg_type = 'notification' if 'id' not in msg else f'request #{msg["id"]}' if 'params' in msg else f'response #{msg["id"]}'
            lsp.logger.log(f"Jedi LSP: {source} -> {target} {msg_type}:\n{json.dumps(msg)}", logging.DEBUG)
        lsp.server.logger = logging_fn

    async with lsp.start_server():
        yield lsp


async def main():
    proj_root = Path(__file__).parent.parent
    test_root = proj_root / "testRoot"
    python_path = proj_root / ".venv/bin/python"
    demo1_path = test_root / 'demo1.py'

    async with \
            start_pyright(src_root=test_root, python_path=python_path) as lsp_pyright, \
            start_jedi(src_root=test_root) as lsp_jedi:
        with lsp_pyright.open_file(relative_file_path='demo1.py'), lsp_jedi.open_file(relative_file_path='demo1.py'):
            logger.info("Requesting sematic tokens...")
            res = await lsp_jedi.server.send_request(
                method='textDocument/semanticTokens/full',
                params={
                    'textDocument': {
                        "uri": demo1_path.as_uri(),
                    }
                }
            )
            logger.info("Semantic tokens:\n" + json.dumps(res, indent=2, ensure_ascii=False))

            logger.info("Requesting definition of G_VAR in demo1.py...")
            res = await lsp_pyright.request_definition(
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

            res = await lsp_pyright.request_document_symbols(relative_file_path='demo1.py')
            logger.info("Document symbols:\n" + json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
