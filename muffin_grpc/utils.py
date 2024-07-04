"""GRPC Utils."""

from __future__ import annotations

import re
import time
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Dict, Union

from proto_schema_parser.parser import Parser

if TYPE_CHECKING:
    from pathlib import Path

RE_PROTO_COMMENT = re.compile(r"//.*?\n+", re.DOTALL)
RE_IMPORT_PB2 = re.compile(r"^import (\S+)_pb2", re.MULTILINE)


def _parse_proto(proto: Path) -> Dict[str, list[Any]]:
    data = defaultdict(list)
    for st in Parser().parse(proto.read_text()).file_elements:
        data[type(st).__name__].append(st)

    return data


def _is_newer(target: Path, ts: float) -> bool:
    return target.is_file() and target.stat().st_ctime > ts


def _fix_imports(*targets: Path):
    for target in targets:
        text = target.read_text()
        text = RE_IMPORT_PB2.sub(r"from . import \1_pb2", text)
        target.write_text(text)


def _generate_file(target: Path, *lines: Union[str, bool]):
    timestamp = time.time()
    target.write_text(
        f"# {timestamp:.0f}: Generated by the Muffin GRPC Plugin\n"
        + "\n".join([str(line) for line in lines if line]),
    )
