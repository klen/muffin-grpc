"""Support GRPC for Muffin Framework."""
import asyncio
import time
import typing as t
from importlib import import_module
from pathlib import Path
from signal import SIGINT, SIGTERM

import grpc
from asgi_tools._compat import cached_property  # py 37
from grpc_tools import protoc
from muffin import Application
from muffin.plugin import BasePlugin, PluginException
from pkg_resources import resource_filename

from .utils import _parse_proto, _is_newer, _fix_imports, _generate_file


__version__ = '0.1.2'


INCLUDE = resource_filename('grpc_tools', '_proto')


class Plugin(BasePlugin):

    """Start server, register endpoints, connect to channels."""

    name = 'grpc'
    defaults: t.Dict[str, t.Any] = {
        'build_dir': None,
        'server_listen': "[::]:50051",
        'ssl_client': False,
        'ssl_client_params': None,
        'ssl_server': False,
        'ssl_server_params': None,
        'default_channel': 'localhost:50051',
        'default_channel_options': {},
    }

    def __init__(self, *args, **kwargs):
        """Initialize the plugin."""
        super(Plugin, self).__init__(*args, **kwargs)
        self.proto_files = []
        self.services = []

    def setup(self, app: Application, **options):
        """Setup grpc commands."""
        super(Plugin, self).setup(app, **options)

        @app.manage(lifespan=True)
        async def grpc_server():
            """Start GRPC server with the registered endpoints."""
            app.logger.warning('Start GRPC Server')
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
                self.app.logger.warning(f"Build: {path}")
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
                self.cfg.server_listen, grpc.ssl_server_credentials(*self.cfg.ssl_server_params))

        else:
            server.add_insecure_port(self.cfg.server_listen)

        return server

    def add_proto(self, path: t.Union[str, Path], build_dir: t.Union[str, Path] = None):
        """Register/build the given proto file."""
        path = Path(path).absolute()
        self.proto_files.append(path)
        self.build_proto(path, build_dir=build_dir or self.cfg.build_dir)

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
                **(options or self.cfg.default_channel_options)
            )

        return grpc.aio.insecure_channel(
            target=target or self.cfg.default_channel,
            **(options or self.cfg.default_channel_options)
        )

    def build_proto(self, path: t.Union[str, Path],
                    build_dir: t.Union[str, Path] = None) -> t.List[Path]:
        """Build the given proto."""
        targets = []
        args = []
        path = Path(path)
        if not path.exists():
            return []

        proto_updated = path.stat().st_ctime
        build_dir = Path(build_dir or path.parent)
        package, services, imports_ = _parse_proto(path)

        imports: t.List[Path] = [t for name in imports_ for t in self.build_proto(
            path.parent / name, build_dir=build_dir)]

        target_pb2 = build_dir / f"{ path.stem }_pb2.py"
        if not _is_newer(target_pb2, proto_updated):
            targets.append(target_pb2)
            args.append(f"--python_out={ build_dir }")

        if services:
            target_grpc = build_dir / f"{ path.stem }_pb2_grpc.py"
            if not _is_newer(target_grpc, proto_updated):
                targets.append(target_grpc)
                args.append(f"--grpc_python_out={ build_dir }")

        if not targets:
            return []

        timestamp = time.time()

        _generate_file(
            build_dir / '__init__.py', f"# {timestamp:.0f}: Generated by the Muffin GRPC Plugin")

        args = ["grpc_tools.protoc", f"--proto_path={ path.parent }", f"--proto_path={ INCLUDE }",
                *args, str(path)]
        res = protoc.main(args)
        if res != 0:
            raise PluginException('{} failed'.format(" ".join(args)))

        # Fix imports
        _fix_imports(*targets)

        if package:
            _generate_file(build_dir / f"{ package }.py", *[
                f"# {timestamp:.0f}: Generated by the Muffin GRPC Plugin\n",
                *[f"from .{target.stem} import *" for target in imports],
                *[f"from .{ target.stem } import *" for target in targets]
            ])

        return targets
