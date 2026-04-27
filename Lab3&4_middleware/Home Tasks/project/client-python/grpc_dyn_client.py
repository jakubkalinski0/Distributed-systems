from __future__ import annotations

import argparse
from typing import Iterator

import grpc
from google.protobuf import descriptor_pb2, descriptor_pool, message_factory
from grpc_reflection.v1alpha import reflection_pb2, reflection_pb2_grpc


SERVICE_FQN = "smarthome.dyn.DeviceService"


class DynamicSchema:

    def __init__(self, channel: grpc.Channel, service_fqn: str):
        self.channel = channel
        self.service_fqn = service_fqn
        self.pool = descriptor_pool.DescriptorPool()
        self._reflection = reflection_pb2_grpc.ServerReflectionStub(channel)

        files = self._fetch_files_for_symbol(service_fqn)
        self._add_files_to_pool(files)
        self.service = self.pool.FindServiceByName(service_fqn)

    def _fetch_files_for_symbol(self, symbol: str) -> list[descriptor_pb2.FileDescriptorProto]:
        request = reflection_pb2.ServerReflectionRequest(file_containing_symbol=symbol)
        files: list[descriptor_pb2.FileDescriptorProto] = []
        for resp in self._reflection.ServerReflectionInfo(iter([request])):
            if resp.WhichOneof("message_response") == "error_response":
                raise RuntimeError(
                    f"Reflection error: code={resp.error_response.error_code} "
                    f"msg={resp.error_response.error_message!r}"
                )
            for fd_bytes in resp.file_descriptor_response.file_descriptor_proto:
                fd = descriptor_pb2.FileDescriptorProto()
                fd.ParseFromString(fd_bytes)
                files.append(fd)
        return files

    def _add_files_to_pool(self, files: list[descriptor_pb2.FileDescriptorProto]) -> None:
        pending = list(files)
        last_error: Exception | None = None
        added: set[str] = set()
        for _ in range(len(files) + 1):
            still_pending: list[descriptor_pb2.FileDescriptorProto] = []
            progress = False
            for fd in pending:
                if fd.name in added:
                    continue
                try:
                    self.pool.Add(fd)
                    added.add(fd.name)
                    progress = True
                except Exception as ex:
                    last_error = ex
                    still_pending.append(fd)
            pending = still_pending
            if not pending:
                return
            if not progress:
                break
        if pending:
            names = ", ".join(fd.name for fd in pending)
            raise RuntimeError(f"Cannot add files to pool: {names} (last error: {last_error})")

    def message_class(self, fully_qualified_name: str):
        descriptor = self.pool.FindMessageTypeByName(fully_qualified_name)
        return message_factory.GetMessageClass(descriptor)

    def call_path(self, method_name: str) -> str:
        return f"/{self.service.full_name}/{method_name}"

    def method(self, method_name: str):
        for m in self.service.methods:
            if m.name == method_name:
                return m
        raise KeyError(method_name)


def call_unary(channel: grpc.Channel, schema: DynamicSchema, method_name: str, request_msg):
    method = schema.method(method_name)
    InputCls = schema.message_class(method.input_type.full_name)
    OutputCls = schema.message_class(method.output_type.full_name)

    if not isinstance(request_msg, InputCls):
        raise TypeError(f"Expected {InputCls.DESCRIPTOR.full_name}, got {type(request_msg)}")

    rpc = channel.unary_unary(
        schema.call_path(method_name),
        request_serializer=lambda msg: msg.SerializeToString(),
        response_deserializer=OutputCls.FromString,
    )
    return rpc(request_msg)


def call_server_stream(channel: grpc.Channel, schema: DynamicSchema, method_name: str, request_msg) -> Iterator:
    method = schema.method(method_name)
    OutputCls = schema.message_class(method.output_type.full_name)
    rpc = channel.unary_stream(
        schema.call_path(method_name),
        request_serializer=lambda msg: msg.SerializeToString(),
        response_deserializer=OutputCls.FromString,
    )
    return rpc(request_msg)


def cmd_discover(channel: grpc.Channel) -> None:
    stub = reflection_pb2_grpc.ServerReflectionStub(channel)
    req = reflection_pb2.ServerReflectionRequest(list_services="")
    for resp in stub.ServerReflectionInfo(iter([req])):
        if resp.WhichOneof("message_response") == "error_response":
            print(f"  ! reflection error: {resp.error_response.error_message}")
            return
        services = list(resp.list_services_response.service)
        print(f"  discovered {len(services)} services:")
        for s in services:
            print(f"    - {s.name}")
            if s.name == SERVICE_FQN:
                schema = DynamicSchema(channel, s.name)
                for m in schema.service.methods:
                    arrow = "stream" if m.server_streaming else "unary"
                    print(f"        rpc {m.name}({m.input_type.full_name}) "
                          f"returns ({m.output_type.full_name})  [{arrow}]")
        return


def cmd_list(channel: grpc.Channel, kind_filter: str = "") -> None:
    schema = DynamicSchema(channel, SERVICE_FQN)
    ListRequest = schema.message_class("smarthome.dyn.ListRequest")
    req = ListRequest(kindFilter=kind_filter)
    print(f"  -> ListDevices(kindFilter={kind_filter!r})")
    resp = call_unary(channel, schema, "ListDevices", req)
    print(f"  <- {len(resp.devices)} devices:")
    for d in resp.devices:
        attrs = ", ".join(f"{k}={v}" for k, v in d.attributes.items())
        print(f"     {d.id:<10}  kind={d.kind:<11}  on={d.on}   attrs=[{attrs}]")


def cmd_setmode(channel: grpc.Channel, device_id: str, mode_name: str) -> None:
    schema = DynamicSchema(channel, SERVICE_FQN)
    SetModeRequest = schema.message_class("smarthome.dyn.SetModeRequest")
    mode_descriptor = schema.pool.FindEnumTypeByName("smarthome.dyn.Mode")
    if mode_name not in [v.name for v in mode_descriptor.values]:
        names = [v.name for v in mode_descriptor.values]
        print(f"  ! unknown mode '{mode_name}'. Known: {names}")
        return
    mode_value = mode_descriptor.values_by_name[mode_name].number
    req = SetModeRequest(deviceId=device_id, mode=mode_value)
    print(f"  -> SetMode(deviceId={device_id!r}, mode={mode_name})")
    try:
        resp = call_unary(channel, schema, "SetMode", req)
    except grpc.RpcError as ex:
        print(f"  ! REMOTE gRPC error: code={ex.code().name} details={ex.details()!r}")
        return
    attrs = ", ".join(f"{k}={v}" for k, v in resp.attributes.items())
    print(f"  <- DeviceStatus(id={resp.id}, kind={resp.kind}, on={resp.on}, attrs=[{attrs}])")


def cmd_stream(channel: grpc.Channel, device_id: str, samples: int, interval_ms: int) -> None:
    schema = DynamicSchema(channel, SERVICE_FQN)
    StreamRequest = schema.message_class("smarthome.dyn.StreamRequest")
    req = StreamRequest(deviceId=device_id, samples=samples, intervalMs=interval_ms)
    print(f"  -> StreamReadings(deviceId={device_id!r}, samples={samples}, intervalMs={interval_ms})")
    try:
        for i, reading in enumerate(call_server_stream(channel, schema, "StreamReadings", req), start=1):
            print(f"  <- [#{i}] deviceId={reading.deviceId} value={reading.value:.2f} ts={reading.timestampMs}")
    except grpc.RpcError as ex:
        print(f"  ! REMOTE gRPC error: code={ex.code().name} details={ex.details()!r}")


HELP = """\
Komendy:
  discover                                 - listuje uslugi/metody przez Server Reflection
  list [kindFilter]                        - DeviceService.ListDevices (unary)
  setmode <deviceId> <OFF|HEATING|COOLING> - DeviceService.SetMode (unary)
  stream <deviceId> <samples> <intervalMs> - DeviceService.StreamReadings (server-streaming)
  help                                     - ten ekran
  q | quit                                 - wyjscie
"""


def repl(channel: grpc.Channel) -> None:
    print(HELP)
    while True:
        try:
            line = input("grpc-dyn> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not line:
            continue
        parts = line.split()
        cmd, args = parts[0], parts[1:]
        try:
            if cmd in ("q", "quit", "exit"):
                return
            elif cmd == "help":
                print(HELP)
            elif cmd == "discover":
                cmd_discover(channel)
            elif cmd == "list":
                cmd_list(channel, args[0] if args else "")
            elif cmd == "setmode" and len(args) == 2:
                cmd_setmode(channel, args[0], args[1])
            elif cmd == "stream" and len(args) == 3:
                cmd_stream(channel, args[0], int(args[1]), int(args[2]))
            else:
                print("  ! nieznana komenda. Wpisz 'help'.")
        except ValueError as ex:
            print(f"  ! local ValueError: {ex}")
        except grpc.RpcError as ex:
            print(f"  ! gRPC error: code={ex.code().name} details={ex.details()!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Dynamic gRPC client (no compiled stubs)")
    parser.add_argument("--address", default="localhost:50051", help="host:port serwera gRPC")
    parser.add_argument("command", nargs="?", default=None)
    parser.add_argument("rest", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    print(f"[client] connecting to {args.address} (insecure)")
    with grpc.insecure_channel(args.address) as channel:
        try:
            grpc.channel_ready_future(channel).result(timeout=3)
        except grpc.FutureTimeoutError:
            print(f"[client] WARN: serwer pod {args.address} nie odpowiada (timeout 3s).")
        if args.command is None:
            repl(channel)
        else:
            line = " ".join([args.command, *args.rest])
            parts = line.split()
            cmd, rest = parts[0], parts[1:]
            if cmd == "discover":
                cmd_discover(channel)
            elif cmd == "list":
                cmd_list(channel, rest[0] if rest else "")
            elif cmd == "setmode":
                cmd_setmode(channel, rest[0], rest[1])
            elif cmd == "stream":
                cmd_stream(channel, rest[0], int(rest[1]), int(rest[2]))
            else:
                print(f"unknown command: {cmd}")
                return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
