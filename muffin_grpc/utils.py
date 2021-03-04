"""GRPC Utils."""

import re
import typing as t
from pathlib import Path

from .proto3 import proto as parser, Service, Import, Package


RE_PROTO_COMMENT = re.compile(r'//.*?\n+', re.S)
RE_IMPORT_PB2 = re.compile(r'^import (\S+)_pb2', re.MULTILINE)


def _parse_proto(proto: Path) -> t.Tuple[t.Optional[str], t.List[str], t.List[str]]:
    package = None
    services = []
    imports = []
    for st in parser.parse(RE_PROTO_COMMENT.sub('', proto.read_text())).statements:
        if isinstance(st, Service):
            services.append(st.name)

        elif isinstance(st, Import):
            imports.append(st.identifier)

        elif isinstance(st, Package):
            package = st.identifier[0]

    return package, services, imports


def _is_newer(target: Path, ts: float) -> bool:
    return target.is_file() and target.stat().st_ctime > ts


def _fix_imports(*targets: Path):
    for target in targets:
        content = RE_IMPORT_PB2.sub(r'from . import \1_pb2', target.read_text())
        target.write_text(content)


def _generate_file(target: Path, *lines: t.Union[str, bool]):
    target.write_text("\n".join([str(line) for line in lines if line]))
