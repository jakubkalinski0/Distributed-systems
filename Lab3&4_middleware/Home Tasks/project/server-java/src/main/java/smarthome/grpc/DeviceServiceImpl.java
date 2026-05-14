package smarthome.grpc;

import io.grpc.Status;
import io.grpc.stub.StreamObserver;
import smarthome.grpc.proto.DeviceList;
import smarthome.grpc.proto.DeviceServiceGrpc;
import smarthome.grpc.proto.DeviceStatus;
import smarthome.grpc.proto.ListRequest;
import smarthome.grpc.proto.Mode;
import smarthome.grpc.proto.Reading;
import smarthome.grpc.proto.SetModeRequest;
import smarthome.grpc.proto.StreamRequest;

import java.time.LocalTime;
import java.time.format.DateTimeFormatter;
import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;
import java.util.Random;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicReference;

public class DeviceServiceImpl extends DeviceServiceGrpc.DeviceServiceImplBase {

    private static final DateTimeFormatter TIME_FMT = DateTimeFormatter.ofPattern("HH:mm:ss");

    private final Map<String, AtomicReference<DeviceStatus>> devices = new ConcurrentHashMap<>();

    public DeviceServiceImpl() {
        seed("light-1",  "Light",      true,  attrs("brightness", "40"));
        seed("light-2",  "Light",      false, attrs("brightness", "0"));
        seed("clight-1", "ColorLight", true,  attrs("brightness", "80", "color", "255,0,0"));
        seed("thermo-1", "Thermostat", true,  attrs("target", "21.5", "mode", "HEATING"));
        seed("thermo-2", "Thermostat", true,  attrs("target", "18.0", "mode", "COOLING"));
        seed("camera-1", "Camera",     true,  attrs("pan", "0", "tilt", "0", "zoom", "1"));
    }

    @Override
    public void listDevices(ListRequest req, StreamObserver<DeviceList> resp) {
        log("listDevices", "kindFilter=" + req.getKindFilter());

        DeviceList.Builder out = DeviceList.newBuilder();
        for (AtomicReference<DeviceStatus> ref : devices.values()) {
            DeviceStatus d = ref.get();
            if (req.getKindFilter().isEmpty() || req.getKindFilter().equalsIgnoreCase(d.getKind())) {
                out.addDevices(d);
            }
        }
        resp.onNext(out.build());
        resp.onCompleted();
    }

    @Override
    public void setMode(SetModeRequest req, StreamObserver<DeviceStatus> resp) {
        log("setMode", String.format("deviceId=%s mode=%s", req.getDeviceId(), req.getMode()));

        AtomicReference<DeviceStatus> ref = devices.get(req.getDeviceId());
        if (ref == null) {
            resp.onError(Status.NOT_FOUND
                    .withDescription("device not found: " + req.getDeviceId())
                    .asRuntimeException());
            return;
        }
        DeviceStatus current = ref.get();
        if (!"Thermostat".equals(current.getKind())) {
            resp.onError(Status.INVALID_ARGUMENT
                    .withDescription("setMode supported only for Thermostat (got " + current.getKind() + ")")
                    .asRuntimeException());
            return;
        }
        if (req.getMode() == Mode.UNRECOGNIZED) {
            resp.onError(Status.INVALID_ARGUMENT
                    .withDescription("unrecognized mode")
                    .asRuntimeException());
            return;
        }
        DeviceStatus updated = current.toBuilder()
                .putAttributes("mode", req.getMode().name())
                .build();
        ref.set(updated);
        resp.onNext(updated);
        resp.onCompleted();
    }

    @Override
    public void streamReadings(StreamRequest req, StreamObserver<Reading> resp) {
        log("streamReadings", String.format("deviceId=%s samples=%d intervalMs=%d",
                req.getDeviceId(), req.getSamples(), req.getIntervalMs()));

        if (!devices.containsKey(req.getDeviceId())) {
            resp.onError(Status.NOT_FOUND
                    .withDescription("device not found: " + req.getDeviceId())
                    .asRuntimeException());
            return;
        }
        int n = Math.max(1, Math.min(100, req.getSamples()));
        int intervalMs = Math.max(0, Math.min(5_000, req.getIntervalMs()));
        Random rng = new Random();
        try {
            for (int i = 0; i < n; i++) {
                Reading r = Reading.newBuilder()
                        .setDeviceId(req.getDeviceId())
                        .setValue(20.0 + rng.nextDouble() * 5.0)
                        .setTimestampMs(System.currentTimeMillis())
                        .build();
                resp.onNext(r);
                log("  -> reading", String.format(Locale.US, "#%d value=%.2f", i + 1, r.getValue()));
                if (intervalMs > 0 && i < n - 1) {
                    Thread.sleep(intervalMs);
                }
            }
            resp.onCompleted();
        } catch (InterruptedException ex) {
            Thread.currentThread().interrupt();
            resp.onError(Status.CANCELLED.withCause(ex).asRuntimeException());
        }
    }

    private void seed(String id, String kind, boolean on, Map<String, String> attrs) {
        DeviceStatus.Builder b = DeviceStatus.newBuilder()
                .setId(id).setKind(kind).setOn(on);
        attrs.forEach(b::putAttributes);
        devices.put(id, new AtomicReference<>(b.build()));
    }

    private static Map<String, String> attrs(String... kv) {
        if (kv.length % 2 != 0) throw new IllegalArgumentException("attrs requires pairs");
        Map<String, String> m = new LinkedHashMap<>();
        for (int i = 0; i < kv.length; i += 2) m.put(kv[i], kv[i + 1]);
        return m;
    }

    private void log(String op, String args) {
        System.out.printf("[%s][grpc] %s(%s)%n", LocalTime.now().format(TIME_FMT), op, args);
    }
}
