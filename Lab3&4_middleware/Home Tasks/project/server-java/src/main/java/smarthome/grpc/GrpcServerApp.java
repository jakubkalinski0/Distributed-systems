package smarthome.grpc;

import io.grpc.Server;
import io.grpc.ServerBuilder;
import io.grpc.protobuf.services.ProtoReflectionService;

/**
 * Aplikacja serwera gRPC. Eksponuje DeviceService i ProtoReflectionService -
 * to drugie umozliwia dynamicznym klientom (oraz grpcurl/Postman) odkrywanie API
 * bez znajomosci pliku .proto w czasie kompilacji.
 *
 * Argumenty CLI: --port <int> (domyslnie 50051).
 */
public class GrpcServerApp {

    public static void main(String[] args) throws Exception {
        int port = parsePort(args, 50051);

        Server server = ServerBuilder.forPort(port)
                .addService(new DeviceServiceImpl())
                .addService(ProtoReflectionService.newInstance())
                .build()
                .start();

        System.out.println();
        System.out.println("=== gRPC server is up ===");
        System.out.printf("Port             : %d%n", port);
        System.out.println("Services         : smarthome.dyn.DeviceService, grpc.reflection.v1alpha.ServerReflection");
        System.out.println("Try (in another terminal):");
        System.out.printf("  grpcurl -plaintext localhost:%d list%n", port);
        System.out.printf("  grpcurl -plaintext -d '{\"kindFilter\":\"Light\"}' localhost:%d smarthome.dyn.DeviceService/ListDevices%n", port);
        System.out.println("Press Ctrl+C to stop.");
        System.out.println();

        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            System.out.println("[grpc] shutting down...");
            server.shutdown();
        }));

        server.awaitTermination();
    }

    private static int parsePort(String[] args, int defaultPort) {
        for (int i = 0; i < args.length - 1; i++) {
            if ("--port".equals(args[i])) {
                try { return Integer.parseInt(args[i + 1]); } catch (NumberFormatException ignored) {}
            }
        }
        return defaultPort;
    }
}
