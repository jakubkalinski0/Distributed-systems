package smarthome.ice.devices;

import com.zeroc.Ice.Current;
import smarthome.Camera;
import smarthome.DeviceUnavailable;
import smarthome.InvalidParameter;
import smarthome.PTZ;
import smarthome.PowerState;

import java.util.Locale;
import java.util.concurrent.atomic.AtomicInteger;

public class CameraI extends BaseDeviceI implements Camera {

    private static final int FAILURE_AT = 5;

    private PTZ ptz;
    private final AtomicInteger snapshotCount = new AtomicInteger(0);

    public CameraI(String building, String id, PowerState power, PTZ initial) {
        super(building, id, "Camera", power);
        this.ptz = (initial != null) ? new PTZ(initial.pan, initial.tilt, initial.zoom) : new PTZ(0f, 0f, 1);
    }

    @Override
    public synchronized void setPTZ(PTZ position, Current current) throws InvalidParameter {
        log("setPTZ", String.format(Locale.US, "pan=%.1f tilt=%.1f zoom=%d", position.pan, position.tilt, position.zoom));
        if (position == null) {
            throw new InvalidParameter("PTZ must not be null", "ptz");
        }
        if (position.zoom < 1 || position.zoom > 10) {
            throw new InvalidParameter("zoom must be 1..10, got " + position.zoom, "zoom");
        }
        if (position.pan < -180f || position.pan > 180f) {
            throw new InvalidParameter("pan must be -180..180, got " + position.pan, "pan");
        }
        if (position.tilt < -90f || position.tilt > 90f) {
            throw new InvalidParameter("tilt must be -90..90, got " + position.tilt, "tilt");
        }
        this.ptz = new PTZ(position.pan, position.tilt, position.zoom);
    }

    @Override
    public synchronized PTZ getPTZ(Current current) {
        log("getPTZ", "");
        return new PTZ(ptz.pan, ptz.tilt, ptz.zoom);
    }

    @Override
    public String snapshot(Current current) throws DeviceUnavailable {
        int n = snapshotCount.incrementAndGet();
        log("snapshot", "n=" + n);
        if (n >= FAILURE_AT) {
            throw new DeviceUnavailable("camera overheated after " + n + " snapshots, please cool down");
        }
        return id + "-snap-" + n;
    }
}
