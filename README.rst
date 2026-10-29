Muffin-GRPC
############

.. image:: https://github.com/klen/muffin-grpc/workflows/tests/badge.svg
    :target: https://github.com/klen/muffin-grpc/actions
    :alt: Tests Status

.. image:: https://img.shields.io/pypi/v/muffin-grpc
    :target: https://pypi.org/project/muffin-grpc/
    :alt: PyPI Version

**Muffin-GRPC** is a plugin for the Muffin_ framework that brings gRPC support to your application.
It compiles ``.proto`` files, registers generated services on a ``grpc.aio`` server and hands out
client channels.

.. contents::

Features
========

- 📦 Compiles `.proto` files to Python, including imported dependencies
- ⚙️ Simplified gRPC server and client integration
- 🔁 CLI commands to build protos and run the server
- 🧩 Fixes generated imports so compiled modules are importable as a package
- 🧪 Built for asyncio and modern Python standards

Requirements
============

- Python >= 3.11
- `muffin`
- `grpcio`
- `grpcio-tools` — used at runtime: the plugin calls ``grpc_tools.protoc`` to compile protos
- `proto-schema-parser` — used to read ``import``/``package`` declarations from protos

All of them are installed with ``pip install muffin-grpc``.

.. note:: Only the **asyncio** event loop is supported. ``grpc.aio`` binds to the running asyncio
   event loop, so applications running under Trio or Curio (``--aiolib=trio``/``curio``) fail when the
   server or a channel is used — ``grpc.aio.server()``/``insecure_channel()`` need asyncio primitives
   that Trio does not provide.

Installation
============

.. code-block:: shell

    pip install muffin-grpc
    # or
    uv add muffin-grpc

Quick start
===========

Set up the plugin and attach it to your Muffin application:

.. code-block:: python

    from muffin import Application
    from muffin_grpc import Plugin as GRPC

    app = Application("example")
    grpc = GRPC(app, server_listen="[::]:50051")
    grpc.add_proto("project_name/proto/helloworld.proto")

Create ``project_name/proto/helloworld.proto``:

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

Compile the proto files (``add_proto`` already did it if ``autobuild`` is enabled, see below):

.. code-block:: shell

    muffin project_name grpc-build

This generates:

- ``helloworld_pb2.py`` — messages
- ``helloworld_pb2_grpc.py`` — client stubs and server servicers
- ``helloworld.py`` — aggregator module, imports from both files above
- ``__init__.py`` — so the build directory is importable as a package

Implement the Greeter service:

.. code-block:: python

    from grpc.aio import ServicerContext

    from .proto.helloworld import GreeterServicer, HelloReply, HelloRequest


    @grpc.add_to_server
    class Greeter(GreeterServicer):
        async def SayHello(self, request: HelloRequest, context: ServicerContext) -> HelloReply:
            return HelloReply(message=f"Hello, {request.name}!")

Run the gRPC server:

.. code-block:: shell

    muffin project_name grpc-server

And call it from a Muffin view (or any asyncio code):

.. code-block:: python

    from grpc.aio import AioRpcError

    from .proto.helloworld import GreeterStub, HelloRequest


    @app.route("/")
    async def index(request):
        name = request.url.query.get("name", "anonymous")
        try:
            async with grpc.get_channel() as channel:
                stub = GreeterStub(channel)
                response = await stub.SayHello(HelloRequest(name=name), timeout=10)
                return response.message

        except AioRpcError as exc:
            return exc.details()

A complete runnable application (server, web client and templates) lives in the ``example/``
directory of the repository. It needs the ``example`` dependency group (``muffin-jinja2`` and
``uvicorn``):

.. code-block:: shell

    uv sync --group example
    make build        # compile example/proto/src/helloworld.proto
    make example      # web UI on http://localhost:5000
    make example-grpc # gRPC server on [::]:50051

Proto compilation
=================

Registering a proto
-------------------

``add_proto(path, build_dir=None, **params)`` registers a ``.proto`` file and, when ``autobuild`` is
enabled (the default), compiles it immediately:

- ``path`` is resolved to an absolute path and stored in ``plugin.proto_files``;
- ``build_dir`` defaults to the plugin option ``build_dir`` and then to the directory of the
  ``.proto`` file itself;
- ``**params`` are passed to ``build_proto`` — in practice ``build_package``, ``include`` and
  ``targets`` (see below); they are remembered and reused by the ``grpc-build`` command;
- the return value is the list of generated files: the ``*_pb2.py`` module, the ``*_pb2_grpc.py``
  module when the proto declares a ``service``, and the ``*_pb2.py`` files of imported protos.
  With ``autobuild=False`` nothing is written and only the expected ``<name>_pb2.py`` path is
  returned.

``build_proto(path, build_dir=None, *, build_package=None, targets=None, include=None)`` does the
actual work and returns ``[]`` when the file does not exist.

Generated files
---------------

Everything is written to ``build_dir`` (flat, next to each other):

- ``<name>_pb2.py`` — messages;
- ``<name>_pb2_grpc.py`` — stubs and servicers, only for protos with a ``service``;
- ``__init__.py`` — created only when something was rebuilt, contains a generated header comment;
- ``<package>.py`` — an aggregator with ``from .<name>_pb2 import *`` lines for every generated
  module. Its name is ``build_package`` if given, otherwise the last ``package`` declaration of the
  proto. Use ``build_package=False`` to skip it, and note that a proto without a ``package`` and
  without an explicit ``build_package`` produces no aggregator.

Incremental builds
------------------

``build_proto`` compares the change time (``ctime``) of the proto with the ``ctime`` of the target file
(``_is_newer``). Targets that are newer are not regenerated, and when every target is up to date
nothing is written at all — not even ``__init__.py`` or the aggregator. So generated files are only
rewritten when the proto (or a proto it imports) changed. Note that ``ctime`` is the metadata change
time, so e.g. a ``chmod`` on the proto also triggers a rebuild, while a copied file with preserved
timestamps still gets a fresh ``ctime``.

Proto dependencies
------------------

Imports are read with ``proto-schema-parser``: every ``import "..."`` is compiled first (recursively,
depth-first) into the same ``build_dir`` (or ``build_dir/<subdir>`` for imports that carry a
directory in their name), then the importing proto is compiled. Because of that the order of
``add_proto`` calls does not matter for dependencies — but services still have to be registered
before the server is started.

Imports are looked up in the directory of the importing proto, in the ``grpc_tools`` well-known types
(``google/protobuf/*.proto``) and in the extra roots passed as ``include=[path, ...]``. Protos that
live in a different directory than the importer therefore need an explicit ``include``:

.. code-block:: python

    from pathlib import Path

    grpc.add_proto("protos/api/service.proto", include=[Path("protos")])

Import fixing
-------------

``grpc_tools.protoc`` generates absolute imports (``import helloworld_pb2 as ...``), which break as
soon as the generated files live in a package. After a successful compile the plugin rewrites, in
every generated file, lines matching ``^import <name>_pb2`` into ``from . import <name>_pb2``. That is
why ``from .proto.helloworld import GreeterStub`` works and why the build directory must stay
importable as a regular Python package.

Only top-level imports are rewritten. An ``import "sub/base.proto"`` becomes
``from sub import base_pb2`` and stays absolute — keep proto files, or at least their import paths,
flat unless you put the build directory on ``sys.path``.

If ``protoc`` fails, the plugin raises ``PluginError`` with the command it tried to run.

Autobuild
---------

``autobuild`` (default ``True``) controls whether ``add_proto`` compiles the proto right away. It
runs where the plugin is configured — typically at module import time, i.e. when the application
module is loaded::

    grpc = GRPC(app, build_dir=...)   # no proto yet
    grpc.add_proto("protos/api.proto")  # compiles here when autobuild is True

Nothing is compiled in ``startup()``: that method only opens the default channel (see
`Plugin API`_). So with ``autobuild=True`` a stale or missing build is refreshed on every process
start, including production, which costs the compile time and needs a writable build directory.

For production it is better to compile once, before deploying, and to disable the runtime build:

.. code-block:: python

    from pathlib import Path

    grpc = GRPC(app, build_dir=Path("build/proto"), autobuild=False)
    grpc.add_proto("protos/api.proto")

.. code-block:: shell

    muffin project_name grpc-build   # in CI or during deployment

Configuration
=============

You can configure the plugin either via ``setup()`` or using ``GRPC_`` prefixed settings in the
Muffin app config.

**Available options:**

=========================== =========================================== ==============================================================
Name                        Default value                               Description
=========================== =========================================== ==============================================================
**autobuild**               `True`                                      Compile protos when they are registered
**build_dir**               `None`                                      Directory for compiled files, `None` = next to the proto
**server_listen**           `"[::]:50051"`                              gRPC server address
**ssl_server**              `False`                                     Enable SSL for the server
**ssl_server_params**       `None`                                      Tuple of credentials for the SSL server
**ssl_client**              `False`                                     Enable SSL for the client
**ssl_client_params**       `None`                                      Tuple of credentials for the SSL client
**default_channel**         `"localhost:50051"`                         Default gRPC client target
**default_channel_options** `{}`                                        Additional gRPC channel options
=========================== =========================================== ==============================================================

Via ``setup()``:

.. code-block:: python

    grpc.setup(app, server_listen="localhost:40000")

Or from config:

.. code-block:: python

    GRPC_SERVER_LISTEN = "localhost:40000"

Plugin API
==========

``server`` (property)
    A cached ``grpc.aio.Server`` with all registered services. The first access registers services
    and binds ``server_listen`` — a secure port when ``ssl_server`` is enabled (credentials are
    unpacked from ``ssl_server_params``), an insecure one otherwise. Register services before the
    first access, later additions are not picked up.

``add_proto(path, build_dir=None, **params)``
    Register (and by default compile) a proto, see `Proto compilation`_.

``add_to_server(service_cls)``
    Register a servicer class on the server. The class must inherit from a generated ``*Servicer``;
    the plugin finds the generated ``add_<Service>_to_server`` function through the class MRO.
    It is meant to be used as a decorator and returns ``None`` — the decorated name is replaced by
    ``None`` in the module namespace, so call ``grpc.add_to_server(Greeter)`` instead if you need
    to keep the class around.

``get_channel(address=None, **options)``
    Open a channel to ``address`` or to ``default_channel``; raise ``PluginError`` when neither is
    set. Uses ``secure_channel`` with ``ssl_channel_credentials(*ssl_client_params)`` when
    ``ssl_client`` is enabled and ``insecure_channel`` otherwise. The ``options`` are passed to gRPC
    as is; when they are empty, ``default_channel_options`` is used. Note that the two sets are not
    merged: any passed option replaces the configured defaults.

``build_proto(path, build_dir=None, *, build_package=None, targets=None, include=None)``
    Compile one proto (and its imports), return the generated targets. ``targets`` is an existing
    list of paths to extend (used internally for recursion), ``include`` adds ``--proto_path`` roots.

``startup()`` / ``shutdown()``
    On application startup the plugin opens the default channel and remembers it (a
    ``PluginError`` — e.g. ``default_channel = None`` — is ignored, the channel stays ``None``).
    On shutdown the channel is closed. At the moment there is no proto build here, that is what
    ``autobuild`` does at registration time.

CLI Commands
============

All commands are registered by the plugin (Muffin converts underscores to dashes, so the functions
``grpc_build`` and ``grpc_server`` become ``grpc-build`` and ``grpc-server``). Neither takes
arguments.

Build registered proto files:

.. code-block:: shell

    muffin project_name grpc-build

Start the gRPC server:

.. code-block:: shell

    muffin project_name grpc-server

``grpc-server`` starts the cached server (with the services and the SSL configuration above), waits
for ``SIGINT``/``SIGTERM`` and then stops it with a 2 second grace period. Since services are registered on the plugin before the server
is started, the command must run in the same process that imported your application module.

Limitations
===========

- **asyncio only.** Trio and Curio are not supported (see `Requirements`_).
- One server and one default channel per plugin instance; the server is built once and cached.
- Only top-level generated imports are fixed (see `Import fixing`_), keep proto paths flat.
- ``get_channel`` options replace ``default_channel_options`` instead of merging with them.

Bug Tracker
===========

Found a bug or have a suggestion?
Submit an issue here: https://github.com/klen/muffin-grpc/issues

Contributing
============

Want to contribute? Pull requests are welcome!
Development happens at: https://github.com/klen/muffin-grpc

.. code-block:: shell

    make          # uv sync + install pre-commit hooks
    make test     # uv run pytest
    make lint     # pyrefly + ruff

License
=======

Licensed under the `MIT license`_.

.. _Muffin: https://github.com/klen/muffin
.. _MIT license: http://opensource.org/licenses/MIT
