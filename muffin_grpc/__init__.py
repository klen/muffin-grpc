"""Support GRPC for Muffin Framework."""
import asyncio
import logging
import typing as t
from importlib import import_module
from pathlib import Path
from signal import SIGINT, SIGTERM

from grpc_tools import protoc
from muffin import Application
from muffin.plugins import BasePlugin, PluginException
from pkg_resources import resource_filename  # type: ignore

import grpc

# Support python 3.7
try:
    from functools import cached_property  # type: ignore
except ImportError:
    from cached_property import cached_property  # type: ignore

from .utils import _fix_imports, _generate_file, _is_newer, _parse_proto

__version__ = "0.3.5"


INCLUDE = resource_filename("grpc_tools", "_proto")


class Plugin(BasePlugin):

    """Start server, register endpoints, connect to channels."""

    name = "grpc"
    defaults: t.Dict[str, t.Any] = {
        "autobuild": True,
        "build_dir": None,
        "default_channel": "localhost:50051",
        "default_channel_options": {},
        "server_listen": "[::]:50051",
        "ssl_client": False,
        "ssl_client_params": None,
        "ssl_server": False,
        "ssl_server_params": None,
    }
    logger = logging.getLogger("muffin-grpc")

    def __init__(self, *args, **kwargs):
        """Initialize the plugin."""
        super(Plugin, self).__init__(*args, **kwargs)
        self.proto_files = []
        self.services = []

    def setup(self, app: Application, **options):
        """Setup grpc commands."""
        super(Plugin, self).setup(app, **options)
        self.logger = app.logger

        @app.manage(lifespan=True)
        async def grpc_server():
            """Start GRPC server with the registered endpoints."""
            self.logger.warning("Start GRPC Server")
            self.server.add_insecure_port(self.cfg.server_listen)
            await self.server.start()
            loop = asyncio.get_event_loop()
            stop = asyncio.Event()
            loop.add_signal_handler(SIGINT, stop.set)
            loop.add_signal_handler(SIGTERM, stop.set)
            await stop.wait()
            await self.server.stop(2)

        @app.manage
        async def grpc_build():
            """Build registered proto files."""
            for path in self.proto_files:
                self.logger.warning(f"Build: {path}")
                self.build_proto(path, build_dir=self.cfg.build_dir)

        # TODO: Proto specs
        # -----------------
        #  @app.route('proto/specs')
        #  async def proto_specs(request):
        #      pass

    @cached_property
    def server(self) -> grpc.aio.Server:
        """Generate a GRPC server with registered services."""
        server = grpc.aio.server()
        for service_cls, register in self.services:
            register(service_cls(), server)
        if self.cfg.ssl_server:
            server.add_secure_port(
                self.cfg.server_listen,
                grpc.ssl_server_credentials(*self.cfg.ssl_server_params),
            )

        else:
            server.add_insecure_port(self.cfg.server_listen)

        return server

    def add_proto(
        self,
        path: t.Union[str, Path],
        build_dir: t.Union[str, Path] = None,
        build_package: str = None,
        targets: t.List[Path] = None,
    ):
        """Register/build the given proto file."""
        path = Path(path).absolute()
        self.proto_files.append(path)
        if self.cfg.autobuild:
            build_dir = Path(build_dir or self.cfg.build_dir or path.parent)
            return self.build_proto(
                path, build_dir=build_dir, build_package=build_package, targets=targets
            )

    def add_to_server(self, service_cls):
        """Register the given service class to the server."""
        proto_cls = service_cls.mro()[-2]
        proto_module = import_module(proto_cls.__module__)
        register = getattr(proto_module, f"add_{ proto_cls.__name__ }_to_server")
        self.services.append((service_cls, register))

    def channel(self, target: str = None, **options):
        """Open a channel."""
        if self.cfg.ssl_client:
            return grpc.aio.secure_channel(
                target or self.cfg.default_channel,
                grpc.ssl_channel_credentials(*self.cfg.ssl_client_params or ()),
                **(options or self.cfg.default_channel_options),
            )

        return grpc.aio.insecure_channel(
            target=target or self.cfg.default_channel,
            **(options or self.cfg.default_channel_options),
        )

    def build_proto(
        self,
        path: t.Union[str, Path],
        build_dir: t.Union[str, Path] = None,
        build_package: t.Union[str, bool] = None,
        targets: t.List[Path] = None,
    ) -> t.List[Path]:
        """Build the given proto."""
        path = Path(path)
        if not path.exists():
            return []

        proto_updated = path.stat().st_ctime
        build_dir = Path(build_dir or path.parent)
        if not build_dir.exists():
            build_dir.mkdir()

        package, services, imports = _parse_proto(path)
        if build_package is None:
            build_package = package

        targets = targets or []
        targets = targets + [
            target
            for name in imports
            for target in self.build_proto(
                path.parent / name, build_dir=build_dir / Path(name).parent
            )
        ]

        args = []
        target_pb2 = build_dir / f"{ path.stem }_pb2.py"
        targets.append(target_pb2)
        if not _is_newer(target_pb2, proto_updated):
            args.append(f"--python_out={ build_dir }")

        if services:
            target_grpc = build_dir / f"{ path.stem }_pb2_grpc.py"
            targets.append(target_grpc)
            if not _is_newer(target_grpc, proto_updated):
                args.append(f"--grpc_python_out={ build_dir }")

        if args:
            self.logger.info("Build %r", path)

            _generate_file(build_dir / "__init__.py")

            args = [
                "grpc_tools.protoc",
                f"--proto_path={ path.parent }",
                f"--proto_path={ INCLUDE }",
                *args,
                str(path),
            ]
            res = protoc.main(args)
            if res != 0:
                raise PluginException("{} failed".format(" ".join(args)))

            # Fix imports
            _fix_imports(*targets)

            if build_package:
                _generate_file(
                    build_dir / f"{ build_package }.py",
                    *[f"from .{target.stem} import *" for target in targets],
                )

        return targets
