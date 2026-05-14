#pragma once

module smarthome
{
    enum PowerState { Off, On };

    enum HvacMode { ModeOff, Heating, Cooling };

    struct Color {
        int r;
        int g;
        int b;
    };

    struct PTZ {
        float pan;
        float tilt;
        int   zoom;
    };

    struct DeviceInfo {
        string     id;
        string     kind;
        PowerState power;
    };

    sequence<DeviceInfo> DeviceInfoSeq;

    exception DeviceError {
        string reason;
    };

    exception InvalidParameter extends DeviceError {
        string field;
    };

    exception DeviceUnavailable extends DeviceError {
    };

    interface Device {
        idempotent DeviceInfo info();
        void setPower(PowerState p) throws DeviceError;
    };

    interface Light extends Device {
        void setBrightness(int percent) throws InvalidParameter;
        idempotent int getBrightness();
    };

    interface ColorLight extends Light {
        void setColor(Color c) throws InvalidParameter;
        idempotent Color getColor();
    };

    interface Thermostat extends Device {
        void setTarget(float celsius) throws InvalidParameter;
        idempotent float getTarget();
        idempotent void setMode(HvacMode m);
        idempotent HvacMode getMode();
    };

    interface Camera extends Device {
        void setPTZ(PTZ position) throws InvalidParameter;
        idempotent PTZ getPTZ();
        string snapshot() throws DeviceUnavailable;
    };

    interface Building {
        idempotent DeviceInfoSeq listDevices();
        idempotent Device* getDevice(string id) throws DeviceError;
        idempotent string getName();
    };
};
