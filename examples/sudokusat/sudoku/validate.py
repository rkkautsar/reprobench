import itertools
import re
from datetime import datetime
from math import sqrt
from pathlib import Path
from typing import List

import numpy as np
from loguru import logger
from playhouse.apsw_ext import BooleanField, DateTimeField, ForeignKeyField

from reprobench.core.bases import Step
from reprobench.core.db import BaseModel, Run, db
from reprobench.executors.db import RunStatistic


class SudokuVerdict(BaseModel):
    created_at = DateTimeField(default=datetime.now)
    run = ForeignKeyField(Run, backref="sudoku_verdicts", on_delete="cascade")
    is_valid = BooleanField()


class Validator(Step):
    @classmethod
    def register(cls, config={}):
        SudokuVerdict.create_table()

    @classmethod
    def _parse_sudoku(cls, text):
        board = []
        for line in text:
            if line.startswith("+"):
                continue
            blocks = line[2:-2].split(" | ")
            nums = [[num for num in re.split("\s+", block.strip())] for block in blocks]
            board.append(list(itertools.chain.from_iterable(nums)))
        return board

    @classmethod
    def _check_consistency(cls, task, output):
        # Check if output is consistent with input
        for i in range(len(task)):
            for j, char in enumerate(task[i]):
                if char != "_" and output[i][j] != char:
                    return False

        return True

    @classmethod
    def _check_sudoku_constraints(cls, board):
        size = int(sqrt(len(board)))

        def unique(lst):
            return len(set(lst)) == len(lst)

        matrix = np.array(board)

        # row
        for row in matrix:
            if not unique(row):
                return False

        # column
        for col in matrix.transpose():
            if not unique(col):
                return False

        for brow in range(size):
            for bcol in range(size):
                block = matrix[
                    (brow * size) : ((brow + 1) * size),
                    (bcol * size) : ((bcol + 1) * size),
                ].flatten()
                if not unique(block):
                    return False

        return True

    @classmethod
    def _filter_empty_lines(cls, lines):
        return [
            line
            for line in lines
            if len(line.strip()) != 0 and line.startswith(("+", "|"))
        ]

    @classmethod
    def execute(cls, context, config={}):
        task = cls._filter_empty_lines(
            Path(context["run"].task.path).read_text().split("\n")
        )
        output = cls._filter_empty_lines(
            (Path(context["run"].directory) / "run.out").read_text().split("\n")
        )

        is_valid = True

        stats = RunStatistic.get(run=context["run"])
        if stats.verdict != RunStatistic.SUCCESS:
            is_valid = False

        if len(output) < len(task):
            is_valid = False

        if is_valid and config.get("check_consistency", False):
            is_valid = cls._check_consistency(task, output)

        if is_valid:
            parsed = cls._parse_sudoku(output)
            is_valid = cls._check_sudoku_constraints(parsed)

        SudokuVerdict.create(run=context["run"], is_valid=is_valid)
