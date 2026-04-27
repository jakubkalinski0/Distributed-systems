// Slice IDL dla zadania A1 - "Inteligentne otoczenie".
//
// Cele projektu IDL:
//  - kazde urzadzenie = osobny obiekt middleware z wlasnym Identity (np. "light-1");
//  - "bogate" typy: enum, struct, sequence, dziedziczenie interfejsow i wyjatkow;
//  - operacje wykraczajace poza get/set (setPTZ(struct), snapshot(), listDevices());
//  - wyjatki dla wszystkich realnych blednych scenariuszy + dziedziczenie wyjatkow;
//  - zwracanie proxy w wartosci zwracanej (Building.getDevice -> Device*).

#pragma once

module smarthome
{
    /** Stan zasilania urzadzenia. */
    enum PowerState { Off, On };

    /** Tryb pracy termostatu (HVAC). */
    enum HvacMode { ModeOff, Heating, Cooling };

    /** Kolor RGB (kazdy kanal w zakresie 0..255). */
    struct Color {
        int r;
        int g;
        int b;
    };

    /** Pozycja kamery PTZ (Pan/Tilt/Zoom). */
    struct PTZ {
        float pan;
        float tilt;
        int   zoom;
    };

    /** Krotka informacja o urzadzeniu - zwracana w listach i przy odswiezaniu stanu. */
    struct DeviceInfo {
        string     id;
        string     kind;
        PowerState power;
    };

    /** Lista urzadzen zwracana z Building.listDevices(). */
    sequence<DeviceInfo> DeviceInfoSeq;

    // ---- Wyjatki -------------------------------------------------------

    /** Bazowy wyjatek bledow operacji na urzadzeniach. */
    exception DeviceError {
        string reason;
    };

    /** Walidacja parametru sie nie powiodla (np. brightness=200, zoom<1). */
    exception InvalidParameter extends DeviceError {
        string field;
    };

    /** Symulowana awaria sprzetu lub utrata polaczenia z urzadzeniem. */
    exception DeviceUnavailable extends DeviceError {
    };

    // ---- Interfejsy urzadzen -------------------------------------------

    /** Wspolny interfejs dla kazdego urzadzenia w systemie. */
    interface Device {
        /** Aktualne meta-informacje (id, kind, power). */
        idempotent DeviceInfo info();

        /** Zmiana stanu zasilania. Moze rzucic DeviceError przy awarii. */
        void setPower(PowerState p) throws DeviceError;
    };

    /** Zwykla lampa (regulacja jasnosci). */
    interface Light extends Device {
        /** Ustaw jasnosc 0..100. Poza zakresem -> InvalidParameter("brightness"). */
        void setBrightness(int percent) throws InvalidParameter;

        idempotent int getBrightness();
    };

    /** Lampa z regulacja koloru (rozszerza Light). */
    interface ColorLight extends Light {
        /** Ustaw kolor. Komponenty poza 0..255 -> InvalidParameter. */
        void setColor(Color c) throws InvalidParameter;

        idempotent Color getColor();
    };

    /** Termostat z regulacja temperatury i trybu. */
    interface Thermostat extends Device {
        /** Temperatura zadana w stopniach Celsjusza. Poza -50..50 -> InvalidParameter. */
        void setTarget(float celsius) throws InvalidParameter;

        idempotent float getTarget();

        /** Tryb pracy (operacja jest idempotentna - kolejne ustawienie tego samego trybu jest no-op). */
        idempotent void setMode(HvacMode m);

        idempotent HvacMode getMode();
    };

    /** Kamera monitoringu z funkcja PTZ (Pan/Tilt/Zoom). */
    interface Camera extends Device {
        /** Ustawia caly stan PTZ jednym wywolaniem (efektywnie - jedna struktura zamiast 3 setterow). */
        void setPTZ(PTZ position) throws InvalidParameter;

        idempotent PTZ getPTZ();

        /** Wykonuje "zdjecie" - zwraca identyfikator zdjecia. Po N wywolaniach symuluje awarie. */
        string snapshot() throws DeviceUnavailable;
    };

    // ---- Rejestr urzadzen w jednym serwerze ("budynku") ----------------

    /**
     * Glowny obiekt sluzacy do listowania i pobierania referencji do urzadzen
     * w obrebie pojedynczej instancji serwera. Klient laczy sie z Building.* w kazdym
     * z dwoch serwerow Ice.
     */
    interface Building {
        /** Lista urzadzen widocznych w tym serwerze. */
        idempotent DeviceInfoSeq listDevices();

        /**
         * Zwraca proxy do konkretnego urzadzenia. Klient nastepnie robi *Prx.checkedCast
         * aby wykryc rzeczywisty podtyp (Light, ColorLight, Thermostat, Camera).
         * Brak urzadzenia -> DeviceError("not found").
         */
        idempotent Device* getDevice(string id) throws DeviceError;

        /** Czytelna nazwa "budynku" (np. "building-1") - dla logow / UI klienta. */
        idempotent string getName();
    };
};
