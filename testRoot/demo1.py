#!/usr/bin/env python3
# ! -*- coding: utf-8 -*-
import random

from demo2 import TestDemo2

G_VAR = 1


class TestDemo1:
    def test1(self):
        global G_VAR
        if random.random() > 0.5:
            G_VAR = TestDemo2.CLS_VAR
        print(G_VAR)


if __name__ == '__main__':
    test = TestDemo1()
    test.test1()
