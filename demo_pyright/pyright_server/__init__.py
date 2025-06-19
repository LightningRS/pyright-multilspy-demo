#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, List, Optional

from loguru import logger as loguru_logger
from multilspy import multilspy_types
from multilspy.language_server import LanguageServer
from multilspy.lsp_protocol_handler.lsp_types import InitializeParams
from multilspy.lsp_protocol_handler.server import ProcessLaunchInfo
from multilspy.multilspy_config import MultilspyConfig
from multilspy.multilspy_logger import MultilspyLogger


class MultilspyLoguruLogger(MultilspyLogger):
    """Use loguru for logging.
    """
    # noinspection PyMissingConstructor
    def __init__(self) -> None:
        self.logger = loguru_logger.bind(name="multilspy")

    def log(self, debug_message: str, level: int, sanitized_error_message: str = "") -> None:
        self.logger.log(
            logging.getLevelName(level),
            debug_message,
        )


class PyRightServer(LanguageServer):
    def __init__(
            self,
            config: MultilspyConfig,
            logger: MultilspyLoguruLogger,
            repository_root_path: str,
            python_path: Optional[Path] = None,
    ):
        pyright_root = Path(__file__).parent.parent.parent / "third_party" / "pyright" / "package"
        super().__init__(
            config,
            logger,
            repository_root_path,
            ProcessLaunchInfo(
                cmd=f"node {pyright_root / 'langserver.index.js'} --stdio",
                cwd=repository_root_path
            ),
            "python",
        )
        self.python_path = str(python_path) if python_path else 'python'

        if config.trace_lsp_communication:
            # Dump JSON string when tracing lsp communication.
            def logging_fn(source, target, msg):
                self.logger.log(f"LSP: {source} -> {target}:\n{json.dumps(msg)}", logging.DEBUG)
            self.server.logger = logging_fn

    def _get_initialize_params(self, repository_absolute_path: str) -> InitializeParams:
        with open(Path(__file__).parent / "initialize_params.json", "r") as f:
            d: InitializeParams = json.load(f)
        d.pop('_description')
        d["processId"] = os.getpid()
        d["rootPath"] = repository_absolute_path
        d["rootUri"] = Path(repository_absolute_path).as_uri()
        d["workspaceFolders"] = [
            {
                "uri": Path(repository_absolute_path).as_uri(),
                "name": os.path.basename(repository_absolute_path),
            }
        ]
        return d

    @asynccontextmanager
    async def start_server(self) -> AsyncIterator["PyRightServer"]:
        async def execute_client_command_handler(params):
            return []

        async def do_nothing(params):
            return

        async def window_log_message(msg):
            self.logger.log(f"LSP: window/logMessage: {msg}", logging.INFO)

        self.server.on_request("client/registerCapability", do_nothing)
        self.server.on_notification("language/status", do_nothing)
        self.server.on_notification("window/logMessage", window_log_message)
        self.server.on_request("workspace/executeClientCommand", execute_client_command_handler)
        self.server.on_notification("$/progress", do_nothing)
        self.server.on_notification("textDocument/publishDiagnostics", do_nothing)
        self.server.on_notification("language/actionableNotification", do_nothing)

        async with super().start_server():
            self.logger.log("Starting pyright server process", logging.INFO)
            await self.server.start()
            initialize_params = self._get_initialize_params(self.repository_root_path)
            await self.server.send.initialize(initialize_params)
            self.server.notify.initialized({})
            self.server.send_notification(
                method="workspace/didChangeConfiguration",
                params={
                    "settings": {
                        "python": {
                            "pythonPath": self.python_path,
                        },
                        "pyright": {
                            "disableLanguageServices": False,
                            "disableTaggedHints": False,
                            "disableOrganizeImports": False,
                            "disablePullDiagnostics": False,
                            "trace": {"server": "verbose"},
                        },
                    }
                },
            )

            yield self

            # await self.server.shutdown()
            await self.server.stop()

    async def request_definition(
            self, relative_file_path: str, line: int, column: int
    ) -> List[multilspy_types.Location]:
        try:
            return await super().request_definition(relative_file_path, line, column)
        except AssertionError:
            # Don't raise AssertionError when failed to request definition.
            return []
