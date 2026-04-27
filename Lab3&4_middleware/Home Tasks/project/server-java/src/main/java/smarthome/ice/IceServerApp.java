package smarthome.ice;

import com.zeroc.Ice.Communicator;
import com.zeroc.Ice.InitializationData;
import com.zeroc.Ice.ObjectAdapter;
import com.zeroc.Ice.Util;
import smarthome.Color;
import smarthome.Device;
import smarthome.HvacMode;
import smarthome.PTZ;
import smarthome.PowerState;
import smarthome.ice.devices.CameraI;
import smarthome.ice.devices.ColorLightI;
import smarthome.ice.devices.LightI;
import smarthome.ice.devices.ThermostatI;

import java.io.FileInputStream;
import java.io.IOException;
import java.util.Properties;

public class IceServerApp {

    public static void main(String[] args) {
        String configPath = parseArg(args, "--config");
        if (configPath == null) {
            System.err.println("Usage: IceServerApp --config <path/to/building.properties>");
            System.exit(1);
        }

        Properties cfg = new Properties();
        try (FileInputStream in = new FileInputStream(configPath)) {
            cfg.load(in);
        } catch (IOException e) {
            System.err.println("Cannot load config '" + configPath + "': " + e.getMessage());
            System.exit(1);
        }

        String name = cfg.getProperty("building.name", "building");
        String endpoints = cfg.getProperty("building.endpoints", "tcp -p 10000");

        InitializationData id = new InitializationData();
        id.properties = Util.createProperties();
        id.properties.setProperty("BuildingAdapter.Endpoints", endpoints);
        id.properties.setProperty("Ice.ThreadPool.Server.Size", "4");
        id.properties.setProperty("Ice.ThreadPool.Server.SizeMax", "8");
        id.properties.setProperty("Ice.Warn.Connections", "1");

        try (Communicator communicator = Util.initialize(args, id)) {
            ObjectAdapter adapter = communicator.createObjectAdapter("BuildingAdapter");

            BuildingI building = new BuildingI(name, adapter);

            String list = cfg.getProperty("devices", "");
            for (String dev : list.split(",")) {
                dev = dev.trim();
                if (dev.isEmpty()) continue;
                Device impl = createDevice(name, dev, cfg);
                building.addDevice(dev, impl);
            }

            adapter.add(building, Util.stringToIdentity("building"));
            adapter.activate();

            System.out.println();
            System.out.printf("=== Ice server '%s' is up ===%n", name);
            System.out.printf("Endpoints       : %s%n", endpoints);
            System.out.printf("Building proxy  : building:%s%n", endpoints);
            System.out.printf("Devices         : %s%n", list);
            System.out.println("Press Ctrl+C to stop.");
            System.out.println();

            communicator.waitForShutdown();
        }
    }

    private static String parseArg(String[] args, String flag) {
        for (int i = 0; i < args.length - 1; i++) {
            if (flag.equals(args[i])) return args[i + 1];
        }
        return null;
    }

    private static Device createDevice(String building, String id, Properties cfg) {
        String kind = required(cfg, id + ".kind");
        PowerState power = "On".equalsIgnoreCase(cfg.getProperty(id + ".power", "Off"))
                ? PowerState.On : PowerState.Off;

        switch (kind) {
            case "Light": {
                int b = Integer.parseInt(cfg.getProperty(id + ".brightness", "0"));
                return new LightI(building, id, power, b);
            }
            case "ColorLight": {
                int b = Integer.parseInt(cfg.getProperty(id + ".brightness", "0"));
                int[] rgb = parseRgb(cfg.getProperty(id + ".color", "255,255,255"));
                return new ColorLightI(building, id, power, b, new Color(rgb[0], rgb[1], rgb[2]));
            }
            case "Thermostat": {
                float t = Float.parseFloat(cfg.getProperty(id + ".target", "20.0"));
                HvacMode mode = HvacMode.valueOf(cfg.getProperty(id + ".mode", "ModeOff"));
                return new ThermostatI(building, id, power, t, mode);
            }
            case "Camera": {
                float pan = Float.parseFloat(cfg.getProperty(id + ".pan", "0"));
                float tilt = Float.parseFloat(cfg.getProperty(id + ".tilt", "0"));
                int zoom = Integer.parseInt(cfg.getProperty(id + ".zoom", "1"));
                return new CameraI(building, id, power, new PTZ(pan, tilt, zoom));
            }
            default:
                throw new IllegalArgumentException(
                        "Unknown device kind '" + kind + "' for id '" + id + "'");
        }
    }

    private static String required(Properties cfg, String key) {
        String v = cfg.getProperty(key);
        if (v == null) throw new IllegalArgumentException("Missing required config key: " + key);
        return v;
    }

    private static int[] parseRgb(String s) {
        String[] parts = s.split(",");
        if (parts.length != 3) throw new IllegalArgumentException("Bad RGB: " + s);
        int[] rgb = new int[3];
        for (int i = 0; i < 3; i++) rgb[i] = Integer.parseInt(parts[i].trim());
        return rgb;
    }
}
