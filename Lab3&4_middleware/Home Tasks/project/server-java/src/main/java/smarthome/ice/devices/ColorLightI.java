package smarthome.ice.devices;

import com.zeroc.Ice.Current;
import smarthome.Color;
import smarthome.ColorLight;
import smarthome.InvalidParameter;
import smarthome.PowerState;

public class ColorLightI extends LightI implements ColorLight {

    private Color color;

    public ColorLightI(String building, String id, PowerState power, int brightness, Color initialColor) {
        super(building, id, "ColorLight", power, brightness);
        this.color = (initialColor != null) ? new Color(initialColor.r, initialColor.g, initialColor.b) : new Color(255, 255, 255);
    }

    @Override
    public synchronized void setColor(Color c, Current current) throws InvalidParameter {
        log("setColor", String.format("rgb=%d,%d,%d", c.r, c.g, c.b));
        if (c == null) {
            throw new InvalidParameter("color must not be null", "color");
        }
        if (!inRange(c.r) || !inRange(c.g) || !inRange(c.b)) {
            throw new InvalidParameter(
                    String.format("color components must be 0..255, got %d,%d,%d", c.r, c.g, c.b), "color");
        }
        this.color = new Color(c.r, c.g, c.b);
    }

    @Override
    public synchronized Color getColor(Current current) {
        log("getColor", "");
        return new Color(color.r, color.g, color.b);
    }

    private static boolean inRange(int v) { return v >= 0 && v <= 255; }
}
