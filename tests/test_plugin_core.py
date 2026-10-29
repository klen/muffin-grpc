from types import SimpleNamespace

import grpc
import pytest
from muffin import Application

import muffin_grpc
from muffin_grpc import Plugin, PluginError

from .conftest import BUILD_DIR, SRC_DIR


def test_setup_returns_true(app: Application):
    grpc_plugin = Plugin()

    assert grpc_plugin.setup(app) is True
    assert app.plugins["grpc"] is grpc_plugin


def test_setup_disabled(app: Application):
    grpc_plugin = Plugin()

    assert grpc_plugin.setup(app, disabled=True) is False
    assert "grpc" not in app.plugins


def test_setup_renames_plugin(app: Application):
    grpc_plugin = Plugin()

    assert grpc_plugin.setup(app, name="rpc") is True
    assert app.plugins["rpc"] is grpc_plugin


async def test_get_channel_default(app: Application):
    grpc_plugin = Plugin(app, default_channel="localhost:5555")
    channel = grpc_plugin.get_channel()
    assert isinstance(channel, grpc.aio.Channel)
    await channel.close()


def test_get_channel_missing(app: Application):
    grpc_plugin = Plugin(app, default_channel=None)

    with pytest.raises(PluginError):
        grpc_plugin.get_channel()


async def test_server_generation_insecure(app: Application):
    grpc_plugin = Plugin(app, server_listen="[::]:4444")
    grpc_plugin.services = []

    server = grpc_plugin.server
    assert isinstance(server, grpc.aio.Server)


def test_proto_file_does_not_exist(app: Application, caplog):
    grpc_plugin = Plugin(app, build_dir="tests/proto/compiled")

    assert grpc_plugin.build_proto("tests/proto/src/missing.proto") == []
    assert grpc_plugin.add_proto("tests/proto/src/missing.proto") == []
    assert "missing.proto" in caplog.text


async def test_grpc_build_command(app: Application):
    grpc_plugin = Plugin(app, autobuild=False, build_dir=BUILD_DIR)
    grpc_plugin.add_proto(SRC_DIR / "helloworld.proto")
    assert not (BUILD_DIR / "helloworld_pb2.py").exists()

    await app.manage.commands["grpc-build"]()

    assert (BUILD_DIR / "helloworld_pb2.py").exists()
    assert (BUILD_DIR / "helloworld_pb2_grpc.py").exists()


async def test_grpc_server_command(app: Application, monkeypatch):
    class FakeServer:
        def __init__(self):
            self.calls = []

        async def start(self):
            self.calls.append("start")

        async def stop(self, grace):
            self.calls.append(("stop", grace))

    class FakeEvent:
        def set(self): ...

        async def wait(self):
            return True

    class FakeLoop:
        def add_signal_handler(self, sig, callback): ...

    server = FakeServer()
    monkeypatch.setattr(Plugin, "server", property(lambda self: server))
    monkeypatch.setattr(
        muffin_grpc,
        "asyncio",
        SimpleNamespace(Event=FakeEvent, get_event_loop=FakeLoop),
    )

    Plugin(app)
    await app.manage.commands["grpc-server"]()

    # The port is bound by the `server` property, the command must not bind it again
    assert server.calls == ["start", ("stop", 2)]


def test_server_ssl_binds_secure_port_only(app: Application, monkeypatch):
    calls = []

    class FakeServer:
        def add_secure_port(self, address, credentials):
            calls.append(("secure", address))

        def add_insecure_port(self, address):
            calls.append(("insecure", address))

    monkeypatch.setattr(grpc.aio, "server", FakeServer)
    grpc_plugin = Plugin(app, ssl_server=True, ssl_server_params=([(b"key", b"cert")],))

    assert isinstance(grpc_plugin.server, FakeServer)
    assert calls == [("secure", "[::]:50051")]
