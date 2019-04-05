import itertools
import re
from datetime import datetime
from math import sqrt
from pathlib import Path

import numpy as np
from playhouse.apsw_ext import BooleanField, DateTimeField, ForeignKeyField

from reprobench.core.base import Step, Observer
from reprobench.executors.db import BaseModel, Run
from reprobench.utils import send_event

STORE_SUDOKU_VERDICT = b"sudokuverdict:store"


class SudokuVerdict(BaseModel):
    created_at = DateTimeField(default=datetime.now)
    run = ForeignKeyField(Run, backref="sudoku_verdicts", on_delete="cascade")
    is_valid = BooleanField()


class SudokuObserver(Observer):
    SUBSCRIBED_EVENTS = (STORE_SUDOKU_VERDICT,)

    @classmethod
    def handle_event(cls, event_type, payload, **kwargs):
        if event_type == STORE_SUDOKU_VERDICT:
            SudokuVerdict.create(**payload)


class SudokuValidator(Step):
    @classmethod
    def register(cls, config=None):
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
        for i, _ in enumerate(task):
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
    def execute(cls, context, config=None):
        tool = context["tool"](context)
        task = cls._filter_empty_lines(Path(tool.task).read_text().split("\n"))
        output = cls._filter_empty_lines(tool.get_output().decode().split("\n"))

        is_valid = True

        if len(output) < len(task):
            is_valid = False

        if is_valid and config.get("check_consistency", False):
            is_valid = cls._check_consistency(task, output)

        if is_valid:
            parsed = cls._parse_sudoku(output)
            is_valid = cls._check_sudoku_constraints(parsed)

        payload = dict(run=context["run"]["id"], is_valid=is_valid)
        send_event(context["socket"], STORE_SUDOKU_VERDICT, payload)
