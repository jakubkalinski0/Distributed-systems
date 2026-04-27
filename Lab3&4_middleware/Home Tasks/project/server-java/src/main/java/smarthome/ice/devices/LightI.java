package smarthome.ice.devices;

import com.zeroc.Ice.Current;
import smarthome.InvalidParameter;
import smarthome.Light;
import smarthome.PowerState;

public class LightI extends BaseDeviceI implements Light {

    protected int brightness;

    public LightI(String building, String id, PowerState initialPower, int initialBrightness) {
        this(building, id, "Light", initialPower, initialBrightness);
    }

    /** Konstruktor pakietowy uzywany takze przez ColorLightI (zeby DeviceInfo.kind == "ColorLight"). */
    protected LightI(String building, String id, String kind, PowerState initialPower, int initialBrightness) {
        super(building, id, kind, initialPower);
        this.brightness = clamp(initialBrightness);
    }

    @Override
    public synchronized void setBrightness(int percent, Current current) throws InvalidParameter {
        log("setBrightness", String.valueOf(percent));
        if (percent < 0 || percent > 100) {
            throw new InvalidParameter("brightness must be 0..100, got " + percent, "brightness");
        }
        this.brightness = percent;
    }

    @Override
    public synchronized int getBrightness(Current current) {
        log("getBrightness", "");
        return brightness;
    }

    private static int clamp(int v) { return Math.max(0, Math.min(100, v)); }
}
