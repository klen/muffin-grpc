import grpc.aio as grpc_aio

from . import grpc
from .proto.helloworld import GreeterServicer, HelloRequest, HelloReply


@grpc.add_to_server
class Greeter(GreeterServicer):

    async def SayHello(self, request: HelloRequest,
                       context: grpc_aio.ServicerContext) -> HelloReply:
        return HelloReply(message='Hello, %s!' % request.name)
