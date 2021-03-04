Muffin-GRPC
############

.. _description:

Muffin-GRPC -- GRPC support for Muffin_ framework.

Features:

- Automatically build proto files and python helpers for them;
- Automatically connect to default channel;
- Automatically create and run GRPC server from your services;

.. _badges:

.. image:: https://github.com/klen/muffin-grpc/workflows/tests/badge.svg
    :target: https://github.com/klen/muffin-grpc/actions
    :alt: Tests Status

.. image:: https://img.shields.io/pypi/v/muffin-grpc
    :target: https://pypi.org/project/muffin-grpc/
    :alt: PYPI Version

.. _contents:

.. contents::

.. _requirements:

Requirements
=============

- python >= 3.7

.. note:: The plugin supports only asyncio evenloop (not trio)

.. _installation:

Installation
=============

**Muffin-GRPC** should be installed using pip: ::

    pip install muffin-grpc

.. _usage:

Usage
=====

Setup the plugin and connect it into your app:

.. code-block:: python

    from muffin import Application
    from muffin_grpc import Plugin as GRPC

    # Create Muffin Application
    app = Application('example')

    # Initialize the plugin
    # As alternative: grpc = GRPC(app, **options)
    grpc = GRPC(default_channel='server:50051')
    grpc.setup(app)


Lets build a simple helloworld service, with the proto: ::

    syntax = "proto3";

    package helloworld;

    service Greeter {
        rpc SayHello (HelloRequest) returns (HelloReply) {}
    }

    message HelloRequest {
        string name = 1;
    }

    message HelloReply {
        string message = 1;
    }

Put it somewhere and add the file into the grpc plugin:

.. code-block:: python

   grpc.add_proto('project_name/proto/helloworld.proto')


Run the command to build proto files:

.. code-block:: shell

   $ muffin project_name grpc_build

The command will build the files:

- ``project_name/proto/helloworld_pb2.py`` - with the proto's messages
- ``project_name/proto/helloworld_pb2_grpc.py`` - with the proto's GRPC services
- ``project_name/proto/helloworld.py`` - with the messages and services together
- ``project_name/proto/__init__.py`` - to make the build directory a package

.. note:: Muffin-GRPC fixes python imports automatically

Let's implement the Greeter service:

.. code-block:: python

    from .proto.helloworld import GreeterServicer, HelloRequest, HelloReply

    # Connect the service to GRPC server
    @grpc.add_to_server
    class Greeter(GreeterServicer):

        async def SayHello(self, request: HelloRequest,
                        context: grpc_aio.ServicerContext) -> HelloReply:
            return HelloReply(message='Hello, %s!' % request.name)


Run the server with the command:

.. code-block:: shell

   $ muffin package_name grpc_server

The server is working and accepts GRPC request, let's start building a client

.. code-block:: python

    from .proto.helloworld import GreeterStub, HelloRequest

    @app.route('/')
    async def index(request):
        name = request.url.query.get('name') or 'anonymous'
        try:
            async with grpc.channel() as channel:
                stub = GreeterStub(channel)
                response = await stub.SayHello(
                    HelloRequest(name=request.url.query['name']), timeout=10)
                message = response.message

        except AioRpcError as exc:
            message = exc.details()

        return message

The ``/`` endpoint will make a request to the GRPC server and return a message
from the server.


Configuration options
----------------------

=========================== ======================================= =========================== 
Name                        Default value                           Desctiption
--------------------------- --------------------------------------- ---------------------------
**build_dir**               ``None``                                A directory to build proto files
**server_listen**           ``"[::]:50051"``                        Server address
**ssl_server**              ``False``                               Enable SSL for server
**ssl_server_params**       ``None``                                SSL Server Params
**ssl_client**              ``False``                               Enable SSL for client
**ssl_client_params**       ``None``                                SSL Client Params
**default_channel**         ``localhost:50051``                     Default Client Channel Address
**default_channel_options** ``{}``                                  GRPC options for the default channel
=========================== ======================================= =========================== 

You are able to provide the options when you are initiliazing the plugin:

.. code-block:: python

    grpc.setup(app, server_listen='localhost:40000')

Or setup it from ``Muffin.Application`` configuration using the ``GRPC_`` prefix:

.. code-block:: python

   GRPC_SERVER_LISTERN = 'locahost:40000'

``Muffin.Application`` configuration options are case insensitive

CLI Commands
------------

::

    $ muffin project_name grpc_build --help

    usage: muffin grpc_build [-h]

    Build registered proto files.

    optional arguments:
    -h, --help  show this help message and exit

::

    $ muffin project_name grpc_server --help

    usage: muffin grpc_server [-h]

    Start GRPC server with the registered endpoints.

    optional arguments:
    -h, --help  show this help message and exit


.. _bugtracker:

Bug tracker
===========

If you have any suggestions, bug reports or
annoyances please report them to the issue tracker
at https://github.com/klen/muffin-grpc/issues

.. _contributing:

Contributing
============

Development of Muffin-GRPC happens at: https://github.com/klen/muffin-grpc


Contributors
=============

* klen_ (Kirill Klenov)

.. _license:

License
========

Licensed under a `MIT license`_.

.. _links:


.. _klen: https://github.com/klen
.. _Muffin: https://github.com/klen/muffin
.. _MIT license: http://opensource.org/licenses/MIT
