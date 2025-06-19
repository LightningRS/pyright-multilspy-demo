#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, List, Optional

from multilspy import multilspy_types
from multilspy.language_server import LanguageServer
from multilspy.lsp_protocol_handler.lsp_types import InitializeParams
from multilspy.lsp_protocol_handler.server import ProcessLaunchInfo
from multilspy.multilspy_config import MultilspyConfig

from .logger import MultilspyLoguruLogger


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
        self.settings = {
            "python": {
                "analysis": {
                    "autoImportCompletions": True,
                    "autoSearchPaths": True,
                    "extraPaths": [],
                    "stubPath": "typings",
                    "diagnosticMode": "openFilesOnly",
                    "include": [],
                    "exclude": [],
                    "ignore": [],
                    "diagnosticSeverityOverrides": {},
                    "logLevel": "Information",
                    "typeCheckingMode": "standard",
                    "typeshedPaths": [],
                    "useLibraryCodeForTypes": True
                },
                "venvPath": "",
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

        if config.trace_lsp_communication:
            # Dump JSON string when tracing lsp communication.
            def logging_fn(source, target, msg):
                msg_type = 'notification' if 'id' not in msg else f'request #{msg["id"]}' if 'params' in msg else f'response #{msg["id"]}'
                self.logger.log(f"Pyright LSP: {source} -> {target} {msg_type}:\n{json.dumps(msg)}", logging.DEBUG)
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
        async def handle_workspace_configuration(params):
            res = dict()
            for conf_item in params['items']:
                section = conf_item['section']
                if section == 'python':
                    res['python'] = self.settings['python']
                elif section == 'pyright':
                    res['pyright'] = self.settings['pyright']
                elif section == 'python.analysis':
                    res.setdefault('python', dict())['analysis'] = \
                        self.settings['python']['analysis']
            return res

        async def do_nothing(params):
            return

        async def window_log_message(msg):
            self.logger.log(f"Pyright LSP: window/logMessage: {msg}", logging.INFO)

        self.server.on_notification("window/logMessage", window_log_message)

        self.server.on_request("client/registerCapability", do_nothing)
        self.server.on_request("workspace/configuration", handle_workspace_configuration)
        self.server.on_request("workspace/diagnostic/refresh", do_nothing)
        self.server.on_request("client/unregisterCapability", do_nothing)

        async with super().start_server():
            self.logger.log("Starting pyright server process", logging.INFO)
            await self.server.start()
            initialize_params = self._get_initialize_params(self.repository_root_path)
            await self.server.send.initialize(initialize_params)
            self.server.notify.initialized({})
            self.server.send_notification(
                method="workspace/didChangeConfiguration",
                params={"settings": self.settings},
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
