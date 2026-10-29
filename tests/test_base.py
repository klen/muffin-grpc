import asyncio
from pathlib import Path

import grpc.aio as grpc_aio
import pytest

from muffin_grpc import Plugin as GRPC
from muffin_grpc import PluginError
from muffin_grpc.utils import _generate_file

from .conftest import BUILD_DIR

SRC_DIR = Path("tests/proto/src")


async def test_add_to_server(app):

    grpc = GRPC(
        app,
        build_dir=BUILD_DIR,
        server_listen="[::]:4242",
        default_channel="localhost:4242",
    )
    grpc.add_proto(SRC_DIR / "helloworld.proto")

    from tests.proto.compiled.helloworld import (  # type: ignore[]
        GreeterServicer,
        GreeterStub,
        HelloReply,
        HelloRequest,
    )

    @grpc.add_to_server
    class Greeter(GreeterServicer):
        async def SayHello(
            self, request: HelloRequest, context: grpc_aio.ServicerContext
        ) -> HelloReply:
            return HelloReply(message=f"Hello, {request.name.title()}!")

    assert grpc.services
    assert grpc.server

    server_task = asyncio.create_task(grpc.server.start())

    try:
        async with grpc.get_channel() as channel:
            stub = GreeterStub(channel)
            response = await stub.SayHello(HelloRequest(name="mike"), timeout=10)
            assert response.message == "Hello, Mike!"
    finally:
        server_task.cancel()
        await grpc.server.stop(0)
        await server_task


def test_add_to_server_with_mixin(app):
    grpc = GRPC(app, build_dir=BUILD_DIR)
    grpc.add_proto(SRC_DIR / "helloworld.proto")

    from tests.proto.compiled.helloworld import GreeterServicer  # type: ignore[]

    class LogMixin:
        pass

    class Greeter(GreeterServicer, LogMixin):
        pass

    grpc.add_to_server(Greeter)
    assert len(grpc.services) == 1


def test_add_to_server_without_servicer(app):
    grpc = GRPC(app, autobuild=False)

    with pytest.raises(PluginError):
        grpc.add_to_server(type("Plain", (), {}))


def test_generated_file_write_is_atomic(tmp_path, monkeypatch):
    target = tmp_path / "mod.py"
    target.write_text("old")

    def fail(self, other):
        raise OSError("no space left")

    monkeypatch.setattr(Path, "replace", fail)

    with pytest.raises(OSError, match="no space left"):
        _generate_file(target)

    assert target.read_text() == "old"
