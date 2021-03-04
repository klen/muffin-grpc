"""The example uses muffin-grpc plugin to setup a GRPC server/client."""

from pathlib import Path

from muffin import Application
from muffin_grpc import Plugin as GRPC
from muffin_jinja2 import Plugin as Jinja2


app = Application('grpc-example', debug=True, root=Path(__file__).parent)
jinja2 = Jinja2(app, template_folders=[app.cfg.root / 'templates'], auto_reload=True)
grpc = GRPC(app, server="[::]:50051", build_dir=app.cfg.root / 'proto')
grpc.add_proto(grpc.cfg.build_dir / 'src/helloworld.proto')

from .rpc import *      # noqa
from .views import *    # noqa
