import asyncio
from pathlib import Path

import grpc.aio as grpc_aio

from muffin_grpc import Plugin as GRPC

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
            return HelloReply(message=f"Hello, { request.name.title() }!")

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
