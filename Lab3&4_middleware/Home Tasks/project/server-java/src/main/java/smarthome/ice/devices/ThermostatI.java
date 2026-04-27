package smarthome.ice.devices;

import com.zeroc.Ice.Current;
import smarthome.HvacMode;
import smarthome.InvalidParameter;
import smarthome.PowerState;
import smarthome.Thermostat;

public class ThermostatI extends BaseDeviceI implements Thermostat {

    private float target;
    private HvacMode mode;

    public ThermostatI(String building, String id, PowerState power, float target, HvacMode mode) {
        super(building, id, "Thermostat", power);
        this.target = target;
        this.mode = (mode != null) ? mode : HvacMode.ModeOff;
    }

    @Override
    public synchronized void setTarget(float celsius, Current current) throws InvalidParameter {
        log("setTarget", String.valueOf(celsius));
        if (celsius < -50f || celsius > 50f) {
            throw new InvalidParameter("target must be -50..50 C, got " + celsius, "target");
        }
        this.target = celsius;
    }

    @Override
    public synchronized float getTarget(Current current) {
        log("getTarget", "");
        return target;
    }

    @Override
    public synchronized void setMode(HvacMode m, Current current) {
        log("setMode", String.valueOf(m));
        this.mode = (m != null) ? m : HvacMode.ModeOff;
    }

    @Override
    public synchronized HvacMode getMode(Current current) {
        log("getMode", "");
        return mode;
    }
}
