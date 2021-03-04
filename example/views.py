from grpc.aio import AioRpcError

from . import app, grpc, jinja2


@app.route('/')
async def index(request):
    from .proto.helloworld import GreeterStub, HelloRequest

    message = None

    # Ask helloworld service
    if 'name' in request.url.query:
        try:
            async with grpc.channel() as channel:
                stub = GreeterStub(channel)
                response = await stub.SayHello(
                    HelloRequest(name=request.url.query['name']), timeout=10)
                message = response.message

        except AioRpcError as exc:
            message = exc.details()

    return await jinja2.render('index.html', message=message)
