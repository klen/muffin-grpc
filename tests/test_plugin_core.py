import grpc
import pytest
from muffin import Application

from muffin_grpc import Plugin, PluginError


def test_get_channel_default(app: Application):
    grpc_plugin = Plugin(app, default_channel="localhost:5555")
    channel = grpc_plugin.get_channel()
    assert isinstance(channel, grpc.aio.Channel)


def test_get_channel_missing(app: Application):
    grpc_plugin = Plugin(app, default_channel=None)

    with pytest.raises(PluginError):
        grpc_plugin.get_channel()


def test_server_generation_insecure(app: Application):
    grpc_plugin = Plugin(app, server_listen="[::]:4444")
    grpc_plugin.services = []

    server = grpc_plugin.server
    assert isinstance(server, grpc.aio.Server)


def test_proto_file_does_not_exist(app: Application):
    grpc_plugin = Plugin(app, build_dir="tests/proto/compiled")
    result = grpc_plugin.build_proto("tests/proto/src/missing.proto")

    assert result == []
