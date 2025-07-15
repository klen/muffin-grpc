Muffin-GRPC
############

.. image:: https://github.com/klen/muffin-grpc/workflows/tests/badge.svg
    :target: https://github.com/klen/muffin-grpc/actions
    :alt: Tests Status

.. image:: https://img.shields.io/pypi/v/muffin-grpc
    :target: https://pypi.org/project/muffin-grpc/
    :alt: PyPI Version

**Muffin-GRPC** is a plugin for the Muffin_ framework that brings gRPC support to your application.

.. contents::

Features
========

- 📦 Automatically compiles `.proto` files to Python
- ⚙️ Simplified gRPC server and client integration
- 🔁 CLI commands to manage proto compilation and server lifecycle
- 🧩 Automatically handles proto dependencies and import fixes
- 🧪 Designed with asyncio and modern Python standards

Requirements
============

- Python >= 3.10
- `grpcio`
- `grpcio-tools`
- `protobuf`
- `muffin`

.. note:: This plugin supports only the asyncio event loop (Trio is not supported).

Installation
============

Install via pip:

.. code-block:: shell

    pip install muffin-grpc

Usage
=====

Set up the plugin and attach it to your Muffin application:

.. code-block:: python

    from muffin import Application
    from muffin_grpc import Plugin as GRPC

    app = Application("example")
    grpc = GRPC(default_channel="localhost:50051")
    grpc.setup(app)

Create a `helloworld.proto`:

.. code-block:: proto

    syntax = "proto3";

    package helloworld;

    service Greeter {
        rpc SayHello (HelloRequest) returns (HelloReply);
    }

    message HelloRequest {
        string name = 1;
    }

    message HelloReply {
        string message = 1;
    }

Register the file:

.. code-block:: python

    grpc.add_proto("project_name/proto/helloworld.proto")

Compile proto files:

.. code-block:: shell

    muffin project_name grpc_build

This generates:

- `helloworld_pb2.py` — messages
- `helloworld_pb2_grpc.py` — gRPC services
- `helloworld.py` — bundled import helper
- `__init__.py` — so the folder is importable

.. note:: Muffin-GRPC automatically fixes Python imports.

Now implement the Greeter service:

.. code-block:: python

    from .proto.helloworld import GreeterServicer, HelloReply, HelloRequest
    import grpc.aio as grpc_aio

    @grpc.add_to_server
    class Greeter(GreeterServicer):

        async def SayHello(
            self, request: HelloRequest, context: grpc_aio.ServicerContext
        ) -> HelloReply:
            return HelloReply(message=f"Hello, {request.name}!")

Run the gRPC server:

.. code-block:: shell

    muffin project_name grpc_server

Client example:

.. code-block:: python

    from .proto.helloworld import GreeterStub, HelloRequest
    from aiohttp.web import Application, Response

    @app.route("/")
    async def index(request):
        name = request.url.query.get("name", "anonymous")
        try:
            async with grpc.get_channel() as channel:
                stub = GreeterStub(channel)
                response = await stub.SayHello(HelloRequest(name=name), timeout=10)
                return Response(text=response.message)

        except grpc_aio.AioRpcError as exc:
            return Response(text=exc.details())

Configuration
=============

You can configure the plugin either via `setup()` or using `GRPC_` prefixed settings in the Muffin app config.

**Available options:**

=========================== ================================ =========================================
Name                        Default value                    Description
=========================== ================================ =========================================
**build_dir**               `None`                           Directory to store compiled files
**server_listen**           `"[::]:50051"`                   gRPC server address
**ssl_server**              `False`                          Enable SSL for server
**ssl_server_params**       `None`                           Tuple of credentials for SSL server
**ssl_client**              `False`                          Enable SSL for client
**ssl_client_params**       `None`                           Tuple of credentials for SSL client
**default_channel**         `"localhost:50051"`              Default gRPC client target
**default_channel_options** `{}`                             Additional gRPC options
=========================== ================================ =========================================

Via `setup()`:

.. code-block:: python

    grpc.setup(app, server_listen="localhost:40000")

Or from config:

.. code-block:: python

    GRPC_SERVER_LISTEN = "localhost:40000"

CLI Commands
============

Build registered proto files:

.. code-block:: shell

    muffin project_name grpc_build

Start the gRPC server:

.. code-block:: shell

    muffin project_name grpc_server


Bug Tracker
===========

Found a bug or have a suggestion?
Submit an issue here: https://github.com/klen/muffin-grpc/issues

Contributing
============

Want to contribute? Pull requests are welcome!
Development happens at: https://github.com/klen/muffin-grpc

License
=======

Licensed under the `MIT license`_.

.. _Muffin: https://github.com/klen/muffin
.. _MIT license: http://opensource.org/licenses/MIT
