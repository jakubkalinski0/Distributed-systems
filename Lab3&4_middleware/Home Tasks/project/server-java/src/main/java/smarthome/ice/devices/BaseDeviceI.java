package smarthome.ice.devices;

import com.zeroc.Ice.Current;
import smarthome.Device;
import smarthome.DeviceError;
import smarthome.DeviceInfo;
import smarthome.PowerState;

import java.time.LocalTime;
import java.time.format.DateTimeFormatter;

public abstract class BaseDeviceI implements Device {

    private static final DateTimeFormatter TIME_FMT = DateTimeFormatter.ofPattern("HH:mm:ss");

    protected final String building;
    protected final String id;
    protected final String kind;
    protected PowerState power;

    protected BaseDeviceI(String building, String id, String kind, PowerState initialPower) {
        this.building = building;
        this.id = id;
        this.kind = kind;
        this.power = initialPower;
    }

    @Override
    public synchronized DeviceInfo info(Current current) {
        log("info", "");
        return new DeviceInfo(id, kind, power);
    }

    @Override
    public synchronized void setPower(PowerState p, Current current) throws DeviceError {
        log("setPower", String.valueOf(p));
        if (p == null) {
            throw new DeviceError("power state must be On or Off");
        }
        this.power = p;
    }

    protected void log(String op, String args) {
        System.out.printf("[%s][%s][%s] %s(%s)%n",
                LocalTime.now().format(TIME_FMT), building, id, op, args);
    }
}
