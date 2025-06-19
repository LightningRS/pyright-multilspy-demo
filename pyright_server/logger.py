#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
from typing import Optional

from loguru import logger as loguru_logger
from multilspy.multilspy_logger import MultilspyLogger


class MultilspyLoguruLogger(MultilspyLogger):
    """Use loguru for logging.
    """
    # noinspection PyMissingConstructor
    def __init__(self, name: Optional[str] = None) -> None:
        self.logger = loguru_logger.bind(name="multilspy" if not name else name)
        
    def log(self, debug_message: str, level: int, sanitized_error_message: str = "") -> None:
        self.logger.log(
            logging.getLevelName(level),
            debug_message,
        )