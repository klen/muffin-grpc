from muffin_grpc import Plugin as GRPC

from .conftest import BUILD_DIR, SRC_DIR


def test_add_proto_registers_file(app):
    grpc = GRPC(app, autobuild=False, build_dir=BUILD_DIR)
    targets = grpc.add_proto(SRC_DIR / "helloworld.proto", build_package="helloworld")

    # Files should not be generated
    assert not any(t.exists() for t in targets)
    assert len(grpc.proto_files) == 1


def test_add_proto_autobuild(app):
    grpc = GRPC(app, autobuild=True, build_dir=BUILD_DIR)
    grpc.add_proto(SRC_DIR / "helloworld.proto", build_package="helloworld")
    assert grpc.proto_files

    # Files should be generated
    assert (BUILD_DIR / "helloworld_pb2.py").exists()
    assert (BUILD_DIR / "helloworld_pb2_grpc.py").exists()
    assert (BUILD_DIR / "helloworld.py").exists()
    assert (BUILD_DIR / "__init__.py").exists()

    content = (BUILD_DIR / "helloworld_pb2_grpc.py").read_text()
    assert "from . import helloworld_pb2 as helloworld__pb2" in content

    from tests.proto.compiled.helloworld import (  # type: ignore[]
        GreeterServicer,
        GreeterStub,
        HelloReply,
        HelloRequest,
    )

    assert HelloReply
    assert HelloRequest
    assert GreeterServicer
    assert GreeterStub


def test_proto_build_with_imports(app):
    grpc = GRPC(app, build_dir=BUILD_DIR)
    grpc.add_proto(SRC_DIR / "weather_rpc.proto")

    # Основной proto
    assert (BUILD_DIR / "weather_rpc_pb2.py").exists()
    assert (BUILD_DIR / "weather_rpc_pb2_grpc.py").exists()

    # Зависимость
    assert (BUILD_DIR / "weather_pb2.py").exists()

    from tests.proto.compiled.weather import (  # type: ignore[]
        Temperature,
        WeatherRequest,
        WeatherResponse,
        WeatherService,
    )

    assert WeatherRequest
    assert WeatherResponse
    assert WeatherService
    assert Temperature
