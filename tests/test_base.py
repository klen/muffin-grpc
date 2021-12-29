import asyncio
from pathlib import Path

import pytest

import grpc.aio as grpc_aio

BUILD_DIR = Path("tests/proto/compiled")
SRC_DIR = Path("tests/proto/src")


@pytest.fixture(scope="session")
def aiolib():
    return "asyncio", {"use_uvloop": False}


@pytest.fixture(autouse=True)
async def clean_build():
    for path in BUILD_DIR.glob("*.py"):
        path.unlink()


@pytest.fixture
def app():
    from muffin import Application

    return Application()


async def test_proto_build(app):
    from muffin_grpc import Plugin as GRPC

    grpc = GRPC(app, autobuild=False, build_dir=BUILD_DIR)
    grpc.add_proto(SRC_DIR / "helloworld.proto", build_package="helloworld")

    assert not (BUILD_DIR / "helloworld_pb2.py").is_file()
    assert not (BUILD_DIR / "helloworld_pb2_grpc.py").is_file()

    grpc = GRPC(app, build_dir=BUILD_DIR)
    grpc.add_proto(SRC_DIR / "helloworld.proto", build_package="helloworld")

    assert (BUILD_DIR / "helloworld_pb2.py").is_file()
    assert (BUILD_DIR / "helloworld_pb2_grpc.py").is_file()

    content = (BUILD_DIR / "helloworld_pb2_grpc.py").read_text()
    assert "from . import helloworld_pb2 as helloworld__pb2" in content

    assert grpc.proto_files

    from tests.proto.compiled.helloworld import (GreeterServicer, GreeterStub, HelloReply,
                                                 HelloRequest)

    assert HelloReply
    assert HelloRequest
    assert GreeterServicer
    assert GreeterStub


async def test_proto_build_with_dependencies(app):
    from muffin_grpc import Plugin as GRPC

    grpc = GRPC(app, build_dir=BUILD_DIR)
    grpc.add_proto(SRC_DIR / "weather_rpc.proto")

    assert (BUILD_DIR / "weather.py").is_file()
    assert (BUILD_DIR / "weather_rpc_pb2.py").is_file()
    assert (BUILD_DIR / "weather_rpc_pb2_grpc.py").is_file()
    assert (BUILD_DIR / "weather_pb2.py").is_file()

    from tests.proto.compiled.weather import (Temperature, WeatherRequest, WeatherResponse,
                                              WeatherService)

    assert WeatherRequest
    assert WeatherResponse
    assert WeatherService
    assert Temperature


async def test_add_to_server(app):
    from muffin_grpc import Plugin as GRPC

    grpc = GRPC(
        app,
        build_dir=BUILD_DIR,
        server_listen="[::]:4242",
        default_channel="localhost:4242",
    )
    grpc.add_proto(BUILD_DIR / "src/helloworld.proto")

    from tests.proto.compiled.helloworld import (GreeterServicer, GreeterStub, HelloReply,
                                                 HelloRequest)

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
        async with grpc.channel() as channel:
            stub = GreeterStub(channel)
            response = await stub.SayHello(HelloRequest(name="mike"), timeout=10)
            assert response.message == "Hello, Mike!"
    finally:
        server_task.cancel()
        await grpc.server.stop(0)
        await server_task
