package smarthome.ice;

import com.zeroc.Ice.Current;
import com.zeroc.Ice.Object;
import com.zeroc.Ice.ObjectAdapter;
import com.zeroc.Ice.Util;
import smarthome.Building;
import smarthome.Device;
import smarthome.DeviceError;
import smarthome.DeviceInfo;
import smarthome.DevicePrx;

import java.time.LocalTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public class BuildingI implements Building {

    private static final DateTimeFormatter TIME_FMT = DateTimeFormatter.ofPattern("HH:mm:ss");

    private final String name;
    private final ObjectAdapter adapter;
    private final Map<String, Device> devices = new LinkedHashMap<>();

    public BuildingI(String name, ObjectAdapter adapter) {
        this.name = name;
        this.adapter = adapter;
    }

    public void addDevice(String id, Device impl) {
        devices.put(id, impl);
        adapter.add((Object) impl, Util.stringToIdentity(id));
        log(String.format("register %-12s as %s", id, impl.getClass().getSimpleName()));
    }

    @Override
    public DeviceInfo[] listDevices(Current current) {
        List<DeviceInfo> list = new ArrayList<>(devices.size());
        for (Device d : devices.values()) {
            list.add(d.info(current));
        }
        log("listDevices -> " + list.size() + " items");
        return list.toArray(new DeviceInfo[0]);
    }

    @Override
    public DevicePrx getDevice(String id, Current current) throws DeviceError {
        log("getDevice(" + id + ")");
        if (!devices.containsKey(id)) {
            throw new DeviceError("device not found: " + id);
        }
        return DevicePrx.uncheckedCast(adapter.createProxy(Util.stringToIdentity(id)));
    }

    @Override
    public String getName(Current current) {
        log("getName -> " + name);
        return name;
    }

    private void log(String msg) {
        System.out.printf("[%s][%s][building] %s%n", LocalTime.now().format(TIME_FMT), name, msg);
    }
}
