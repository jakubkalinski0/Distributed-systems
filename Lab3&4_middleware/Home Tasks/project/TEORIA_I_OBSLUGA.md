# Kompletny przewodnik po projekcie: A1 (Ice) + I1 (gRPC)

> Cel tego dokumentu: żebyś po przeczytaniu rozumiał **każdą linijkę** kodu, umiał ją wytłumaczyć prowadzącemu, wiedział co uruchomić i wiedział co powiedzieć.

---

## SPIS TREŚCI

0. [Co to jest ten projekt — przegląd aplikacji](#0-co-to-jest-ten-projekt)
1. [Czym jest middleware i po co nam to](#1-czym-jest-middleware)
2. [ZeroC Ice — teoria od podstaw](#2-zeroc-ice--teoria)
3. [Slice IDL — składnia i projekt](#3-slice-idl)
4. [Jak działa serwer Ice w Javie](#4-serwer-ice-java)
5. [Jak działa klient Ice w Pythonie](#5-klient-ice-python)
6. [gRPC — teoria od podstaw](#6-grpc--teoria)
7. [Protobuf IDL — składnia i projekt](#7-protobuf-idl)
8. [Jak działa serwer gRPC w Javie](#8-serwer-grpc-java)
9. [Wywołanie dynamiczne — serce I1](#9-wywołanie-dynamiczne)
10. [Jak działa klient dynamiczny w Pythonie](#10-klient-dynamiczny-python)
11. [Jak uruchomić cały projekt](#11-uruchomienie)
12. [Decyzje projektowe i ich uzasadnienie](#12-decyzje-projektowe)
13. [User Flow — co musisz umieć zrobić i wiedzieć](#13-user-flow)

---

## 0. Co to jest ten projekt

### 0.1 Idea aplikacji — „Inteligentne otoczenie" (A1)

Wyobraź sobie inteligentny budynek z dziesiątkami urządzeń: żarówek, termostatów, kamer. Każde z nich ma swój unikalny identyfikator i można je zdalnie kontrolować. Naszym zadaniem jest zbudowanie systemu, który umożliwia:

- **zdalne sterowanie urządzeniami** (włącz/wyłącz, zmień jasność, ustaw temperaturę, obróć kamerę),
- **odczyt ich stanu** (jaka jest aktualna jasność? w jakim trybie pracuje termostat?),
- **obsługę błędów** (co jeśli podasz nieprawidłową wartość? co jeśli urządzenie się zepsuje?).

Zadanie A1 to właśnie implementacja takiego systemu przy użyciu technologii middleware — konkretnie **ZeroC Ice**.

### 0.2 Co zaimplementowaliśmy w A1

**Cztery typy urządzeń**, tworzące hierarchię (jedno dziedziczy po drugim):

```
Device (wspólna baza — każde urządzenie ma id, kind, power)
├── Light           — żarówka: regulacja jasności (0–100%)
│   └── ColorLight  — żarówka RGB: jasność + kolor (R,G,B)
├── Thermostat      — termostat: temperatura docelowa + tryb (Off/Heating/Cooling)
└── Camera          — kamera PTZ: ustawienie Pan/Tilt/Zoom + zrobienie zdjęcia
```

**Dziesięć instancji urządzeń** rozłożonych na **dwa niezależne serwery** (budynki):

```
building-1 (port 10000)          building-2 (port 10001)
─────────────────────────        ──────────────────────────
light-1    (Light)               light-3    (Light)
light-2    (Light)               clight-2   (ColorLight)
clight-1   (ColorLight)          clight-3   (ColorLight)
thermo-1   (Thermostat)          thermo-2   (Thermostat)
camera-1   (Camera)              camera-2   (Camera)
```

**Jeden klient Python** który łączy się z **oboma serwerami jednocześnie** i pozwala sterować wszystkimi 10 urządzeniami bez restartu — interaktywne menu (REPL).

### 0.3 Co umożliwia klient A1

Po uruchomieniu `ice_client.py` możesz:

```
> list               ← wyświetl wszystkie 10 urządzeń z obu budynków
> d clight-1         ← wejdź w tryb operowania na clight-1
clight-1> info       ← sprawdź id, kind, stan zasilania
clight-1> color 0 255 0  ← zmień kolor na zielony
clight-1> brightness 200 ← spróbuj nieprawidłowej wartości → dostaniesz błąd z serwera
clight-1> back       ← wróć do głównego menu
> d camera-1
camera-1> snapshot   ← zrób zdjęcie (po 5. wywołaniu: błąd "kamera przegrzana")
```

System jest rozproszony — klient i serwery to osobne procesy, komunikujące się przez sieć (TCP). Wszystko co widzisz w kliencie jest wynikiem zdalnych wywołań do Javy.

### 0.4 Idea zadania I1 — „Wywołanie dynamiczne"

Zadanie I1 to demonstracja techniki, w której klient wywołuje zdalne metody **nie wiedząc z góry (w czasie kompilacji) jak wygląda interfejs serwera**.

Normalnie gdy piszesz klienta gRPC:
1. Masz plik `.proto`
2. Kompilujesz go: `protoc smarthome.proto` → `smarthome_pb2.py`
3. Importujesz: `import smarthome_pb2`
4. Wywołujesz: `stub.ListDevices(smarthome_pb2.ListRequest(kindFilter="Light"))`

W I1: **kroków 2 i 3 nie ma**. Klient dowiaduje się co serwer oferuje dopiero podczas działania programu — przez mechanizm Server Reflection. Plik `.proto` nigdy nie dociera do klienta w formie kodu.

### 0.5 Co różni zadanie I1 od A1

| | A1 (Ice) | I1 (gRPC dynamiczne) |
|---|---|---|
| **Cel** | Zbudować system sterowania urządzeniami | Zademonstrować wywołanie bez wcześniejszej znajomości interfejsu |
| **Technologia** | ZeroC Ice | gRPC |
| **Klient** | Używa skompilowanych stubów (`smarthome_ice.py`) | **Nie ma żadnych stubów** — odkrywa interfejs w runtime |
| **Serwer** | 2 osobne procesy (budynki), urządzenia jako osobne obiekty Ice | 1 proces, wszystkie urządzenia obsługiwane przez jedną usługę |
| **Interfejs IDL** | `smarthome.ice` (Slice) | `smarthome.proto` (Protobuf) |
| **Streaming** | Nie | Tak (`StreamReadings` — server-streaming) |
| **Typy danych** | Struktury, sekwencje, enumy, wyjątki | `map<string,string>`, `repeated`, `enum`, `stream` |
| **Co to pokazuje** | Jak działa RPC z bogatym typowaniem i polimorfizmem | Jak działają narzędzia typu `grpcurl`/Postman "od środka" |

### 0.6 Co zaimplementowaliśmy w I1

**Serwer Java** (`GrpcServerApp` + `DeviceServiceImpl`) z trzema metodami:
- `ListDevices` — lista urządzeń, opcjonalnie filtrowana po typie (unary)
- `SetMode` — zmiana trybu termostatu (unary, z obsługą błędów NOT_FOUND / INVALID_ARGUMENT)
- `StreamReadings` — ciągły strumień odczytów temperatury z urządzenia (server-streaming)

Serwer ma włączony **Server Reflection** — udostępnia swój schemat klientom.

**Klient Python** (`grpc_dyn_client.py`) bez żadnych stubów:
- `discover` — pyta serwer "jakie masz usługi i metody?" (przez Reflection)
- `list` — wywołuje `ListDevices` budując klasy wiadomości w pamięci
- `setmode` — wywołuje `SetMode`, tłumacząc nazwy enumów przez deskryptory
- `stream` — wywołuje `StreamReadings` i iteruje przez odpowiedzi

**grpcurl** — narzędzie wiersza poleceń które robi to samo co nasz klient, ale w jednej komendzie. Demonstrujemy je jako dowód, że nasz mechanizm jest "standardowy".

### 0.7 Jak oba zadania są ze sobą powiązane

Oba zadania mówią o tych samych urządzeniach (light-1, thermo-1 itd.), ale **obsługują je przez zupełnie inne technologie i procesy**:

```
                    ┌─────────────────────────────┐
                    │   TWÓJ KOMPUTER              │
                    │                              │
  Python            │  Java (port 10000)           │
  ice_client.py ────┼──► IceServerApp (building-1) │  ← A1
                    │        light-1, thermo-1...  │
                    │                              │
  Python            │  Java (port 10001)           │
  ice_client.py ────┼──► IceServerApp (building-2) │  ← A1
                    │        clight-2, camera-2... │
                    │                              │
  Python            │  Java (port 50051)           │
  grpc_dyn_client ──┼──► GrpcServerApp             │  ← I1
  grpcurl       ────┼──►   (wszystkie urządzenia)  │
                    └─────────────────────────────┘
```

Łącznie podczas prezentacji działają **3 serwery Java** i **2 klienty Python** (+ grpcurl).

---

## 1. Czym jest middleware

**Middleware** to warstwa oprogramowania między aplikacją a siecią, która ukrywa fakt, że wywołujesz coś zdalnego. Zamiast ręcznie otwierać socket, serializować dane, wysyłać bajty i parsować odpowiedź — piszesz po prostu `prx.setBrightness(80)` jak gdyby to była lokalna metoda.

Middleware robi za Ciebie:
- **serializację** danych (np. struct `PTZ` → bajty → struct `PTZ` po drugiej stronie),
- **transport** (TCP, HTTP/2),
- **multiplexing** (wiele połączeń / wiele metod przez jeden socket),
- **obsługę błędów sieciowych** (timeouty, retry, wyjątki),
- **typowanie** — oba końce muszą zgadzać się na jeden interfejs (IDL).

**IDL** (Interface Definition Language) to język niezależny od platformy, w którym opisujesz interfejsy. Kompilujesz IDL i dostajesz **stuby** (po stronie klienta) i **skeletony** (po stronie serwera) w konkretnym języku (Java, Python itd.).

```
           IDL (.ice lub .proto)
                 |
        slice2java / protoc
                 |
      ┌──────────┴──────────┐
   Stub (klient)        Skeleton (serwer)
   LightPrx.java        Light.java (interface)
```

---

## 2. ZeroC Ice — teoria

### 2.1 Kluczowe pojęcia

| Pojęcie | Co to jest |
|---------|-----------|
| **Communicator** | "silnik" Ice w procesie — jeden na aplikację, zarządza połączeniami i wątkami |
| **ObjectAdapter** | "gniazdo serwerowe" — nasłuchuje na endpoincie (np. `tcp -p 10000`) i przekazuje żądania do servantów |
| **Servant** | Twoja klasa Java implementująca interfejs Slice (np. `LightI implements Light`) |
| **Identity** | Unikalna nazwa obiektu w adapterze, np. `"light-1"`. Razem z adapterem tworzy adres obiektu |
| **Proxy** | Obiekt po stronie klienta, przez który woła metody — wygląda jak lokalny obiekt, ale wysyła żądania przez sieć |
| **Endpoint** | Adres sieciowy w formacie Ice: `tcp -h localhost -p 10000` |
| **Proxy string** | Pełny adres w formie tekstowej: `"light-1:tcp -h localhost -p 10000"` |

### 2.2 Jak wygląda przepływ wywołania

```
Klient (Python)              Sieć              Serwer (Java)
─────────────────────────────────────────────────────────────
prx.setBrightness(80)
  │
  │ stub serializuje: id="light-1", op="setBrightness", arg=80
  │──────────────── TCP ──────────────────────────────────────►
                                             ObjectAdapter odbiera
                                             szuka servanta po id "light-1"
                                             wywołuje lightI.setBrightness(80, current)
                                             serwer waliduje, ustawia stan
                                             ◄─────────────── TCP ────────────────
  stub deserializuje odpowiedź
  metoda wraca
```

### 2.3 Komunikator i jego cykl życia

```java
// Inicjalizacja — jeden Communicator na cały serwer
try (Communicator communicator = Util.initialize(args, id)) {
    // ...
    communicator.waitForShutdown(); // blokuje aż do Ctrl+C
}
// Zamknięcie — automatycznie przez try-with-resources
```

`Util.initialize(args, id)` — `args` to argumenty CLI (Ice może przyjmować swoje flagi przez argv), `id` to `InitializationData` z właściwościami (np. endpoints, rozmiar puli wątków).

### 2.4 ObjectAdapter

```java
ObjectAdapter adapter = communicator.createObjectAdapter("BuildingAdapter");
//                                                         ^^^^^^^^^^^^^^
//                                              Nazwa adaptera — prefix dla properties:
//                                              BuildingAdapter.Endpoints = tcp -p 10000
```

Adapter wie pod jakim adresem nasłuchuje, bo szuka w properties `BuildingAdapter.Endpoints`.

Rejestracja servanta:
```java
adapter.add(servant, Util.stringToIdentity("light-1"));
//         ^^^^^^^ implementacja Javy    ^^^^^^^^^^^^ Identity = "light-1"
```

`Util.stringToIdentity("light-1")` tworzy obiekt `Identity` z `name="light-1"`.

Aktywacja:
```java
adapter.activate(); // zaczyna nasłuchiwać — od tej chwili klienci mogą się łączyć
```

### 2.5 Proxy i stringToProxy / checkedCast

**Po stronie klienta:**
```python
base = communicator.stringToProxy("building:tcp -h localhost -p 10000")
# base to ObjectPrx — typ bazowy, nie wiadomo jeszcze "jakiego" interfejsu
building = smarthome.BuildingPrx.checkedCast(base)
# checkedCast wysyła do serwera pytanie: "czy ten obiekt implementuje interfejs Building?"
# serwer odpowiada listą ice_ids (np. ["::Ice::Object", "::smarthome::Building"])
# jeśli tak → zwraca BuildingPrx, jeśli nie → zwraca None
```

**Dlaczego `checkedCast` a nie `uncheckedCast`?**
- `checkedCast` → wysyła request `ice_isA("::smarthome::Building")` do serwera — pewność typów, jeden dodatkowy RTT
- `uncheckedCast` → tylko rzutuje lokalnie, bez weryfikacji — szybsze, ale ryzykowne

W `BuildingI.getDevice()` używamy `uncheckedCast` bo wiemy, że obiekt istnieje — to my go zarejestrowaliśmy.

### 2.6 Thread pool

Ice obsługuje wywołania równolegle. W configu:
```properties
Ice.ThreadPool.Server.Size    = 4
Ice.ThreadPool.Server.SizeMax = 8
```
Czyli jeśli 3 klientów wywoła metodę jednocześnie, obsłużą je 3 różne wątki z puli. Dlatego każda klasa `*I` ma synchronizację (`synchronized` na metodach).

---

## 3. Slice IDL

### 3.1 Podstawowa składnia

```slice
module smarthome {           // przestrzeń nazw — jak package w Javie
    enum PowerState { Off, On };   // enum: wartości jako identyfikatory
    struct Color { int r; int g; int b; };  // struct: pola z typem
    sequence<DeviceInfo> DeviceInfoSeq;     // sekwencja (lista) typów złożonych
    exception DeviceError { string reason; }; // wyjątek z polami
    exception InvalidParameter extends DeviceError { string field; }; // dziedziczenie wyjątku
    interface Device { ... };                // interfejs
    interface Light extends Device { ... };  // dziedziczenie interfejsu
};
```

### 3.2 Typy proste w Slice

| Slice | Java | Python |
|-------|------|--------|
| `int` | `int` | `int` |
| `float` | `float` | `float` |
| `string` | `String` | `str` |
| `bool` | `boolean` | `bool` |
| `long` | `long` | `int` |
| `void` | `void` | `None` |

### 3.3 Słowo kluczowe `idempotent`

```slice
idempotent DeviceInfo info();
```

`idempotent` mówi Ice, że wywołanie tej metody wielokrotnie z tymi samymi parametrami daje ten sam efekt (i nie zmienia stanu serwera). Ice może wtedy bezpiecznie **powtórzyć** wywołanie automatycznie w przypadku błędów sieciowych (np. zerwane połączenie). Bez `idempotent` Ice tego nie robi, bo nie wie czy wielokrotne wywołanie jest bezpieczne.

Przykłady z projektu:
- `idempotent DeviceInfo info()` — odczyt, OK do powtarzania
- `idempotent void setMode(HvacMode m)` — ustawienie tego samego trybu dwukrotnie = no-op, więc idempotentne
- `void setBrightness(int percent)` — bez idempotent, Ice nie powtarza

### 3.4 Proxy jako wartość zwracana — `Device*`

```slice
idempotent Device* getDevice(string id) throws DeviceError;
```

`Device*` to typ proxy — metoda zwraca referencję do innego obiektu Ice. Klient dostaje gotowy proxy do urządzenia i może od razu wywołać na nim metody. Nie musi sam budować proxy string — dostaje go z serwera.

### 3.5 Dziedziczenie interfejsów

```
Device (info, setPower)
├── Light (setBrightness, getBrightness)  extends Device
│   └── ColorLight (setColor, getColor)  extends Light
├── Thermostat (setTarget, getTarget, setMode, getMode)  extends Device
└── Camera (setPTZ, getPTZ, snapshot)  extends Device
```

`ColorLight` implementuje **wszystkie** metody: `info`, `setPower`, `setBrightness`, `getBrightness`, `setColor`, `getColor`. Dziedziczenie jest polimorficzne — proxy `LightPrx` też działa z obiektem `ColorLight`.

### 3.6 Co generuje `slice2java` i `slice2py`

Z `smarthome.ice` generowane są:
- `Device.java` — interfejs Java (servant musi go implementować)
- `DevicePrx.java` — klasa proxy (klient używa tego)
- `LightI` (nie generowane) — Twoja implementacja
- `Color.java`, `PTZ.java`, `DeviceInfo.java` — klasy struktury
- `HvacMode.java`, `PowerState.java` — enumy
- `DeviceError.java`, `InvalidParameter.java`, `DeviceUnavailable.java` — wyjątki
- `DeviceInfoSeqHelper.java` — helper do serializacji sekwencji

```
┌─── smarthome.ice ─────────────────┐
│  slice2java ──► target/generated/ │
│  slice2py   ──► client-python/generated/ │
└───────────────────────────────────┘
```

**Dlaczego stuby są w osobnym katalogu od źródeł?**
Wymóg z "Uwag wspólnych". Pliki generowane mogą się zmienić po rekompilacji IDL i nie powinny mieszać się z ręcznie pisanym kodem.

---

## 4. Serwer Ice (Java)

### 4.1 Hierarchia klas

```
smarthome.Building (interfejs z IDL)
└── BuildingI implements Building       ← "rejestr" urządzeń

smarthome.Device (interfejs z IDL)
└── BaseDeviceI implements Device       ← id, kind, power + log()
    ├── LightI extends BaseDeviceI, implements Light       ← brightness
    │   └── ColorLightI extends LightI, implements ColorLight ← + color
    ├── ThermostatI extends BaseDeviceI, implements Thermostat ← target, mode
    └── CameraI extends BaseDeviceI, implements Camera     ← PTZ, snapshot
```

**Dlaczego `BaseDeviceI`?** — eliminuje duplikację: każde urządzenie ma `info()` i `setPower()`. Zamiast pisać je 4 razy, dziedziczymy.

### 4.2 `IceServerApp` — co się dzieje krok po kroku

```java
// 1. Wczytanie pliku .properties (building-1.properties)
Properties cfg = new Properties();
cfg.load(new FileInputStream(configPath));

// 2. Przygotowanie InitializationData — tu ustawiamy endpointy i pulę wątków
InitializationData id = new InitializationData();
id.properties = Util.createProperties();
id.properties.setProperty("BuildingAdapter.Endpoints", "tcp -h localhost -p 10000");
id.properties.setProperty("Ice.ThreadPool.Server.Size", "4");

// 3. Inicjalizacja komunikatora
try (Communicator communicator = Util.initialize(args, id)) {

    // 4. Stworzenie adaptera — nasłuchuje na endpoincie
    ObjectAdapter adapter = communicator.createObjectAdapter("BuildingAdapter");

    // 5. Stworzenie BuildingI — wie o adapterze, żeby móc budować proxy
    BuildingI building = new BuildingI("building-1", adapter);

    // 6. Dla każdego urządzenia z configu: stwórz servant, dodaj do adaptera i building
    building.addDevice("light-1", new LightI("building-1", "light-1", PowerState.On, 40));
    //  adapter.add(lightI, Identity("light-1")) ← dzieje się wewnątrz addDevice

    // 7. Zarejestruj Building pod identity "building"
    adapter.add(building, Util.stringToIdentity("building"));

    // 8. Aktywuj adapter — teraz klienci mogą się łączyć
    adapter.activate();

    // 9. Czekaj na shutdown (Ctrl+C)
    communicator.waitForShutdown();
}
```

### 4.3 `BuildingI.getDevice()` — jak klient dostaje proxy do urządzenia

```java
@Override
public DevicePrx getDevice(String id, Current current) throws DeviceError {
    if (!devices.containsKey(id)) {
        throw new DeviceError("device not found: " + id);
    }
    // adapter.createProxy(identity) tworzy proxy wskazujące na ten adapter
    // uncheckedCast bo WIEMY że obiekt jest Device
    return DevicePrx.uncheckedCast(adapter.createProxy(Util.stringToIdentity(id)));
}
```

Klient dostaje proxy już z informacją o endpoincie (embedded w proxy). Nie musi znać adresu urządzenia — zna tylko `Building`.

### 4.4 Wyjątki Ice — jak przechodzą przez sieć

Gdy serwer rzuca:
```java
throw new InvalidParameter("brightness must be 0..100, got 200", "brightness");
```

Ice automatycznie:
1. Serializuje obiekt wyjątku (pola `reason`, `field`) do bajtów.
2. Wysyła go przez TCP w odpowiedzi zamiast wartości zwracanej.
3. Po stronie klienta deserializuje i rzuca ten sam wyjątek.

Klient łapie go jak lokalny:
```python
except smarthome.InvalidParameter as ex:
    print(f"field='{ex.field}' reason='{ex.reason}'")
```

**Ważne:** wyjątki muszą być zadeklarowane w IDL (`throws InvalidParameter`). Niezadeklarowany wyjątek przerwie połączenie.

---

## 5. Klient Ice (Python)

### 5.1 Inicjalizacja i proxy string

```python
with Ice.initialize() as communicator:
    base = communicator.stringToProxy("building:tcp -h localhost -p 10000")
```

Format proxy stringa: `<identity>:<endpoint>` lub `<identity>:<endpoint1>:<endpoint2>`.

`communicator.stringToProxy()` → parsuje string, zwraca `ObjectPrx`. Nie tworzy jeszcze połączenia! Połączenie tworzy się przy pierwszym wywołaniu metody.

### 5.2 `sys.path` i generowane moduły

```python
_GEN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "generated")
sys.path.insert(0, _GEN)
import smarthome  # ładuje client-python/generated/smarthome/__init__.py
```

`slice2py` wygenerował w `client-python/generated/`:
- `smarthome_ice.py` — wszystkie klasy (proxy, struktury, wyjątki)
- `smarthome/__init__.py` — pakiet ładujący `smarthome_ice`

### 5.3 `checkedCast` — jak klient wykrywa podtyp

Problem: `Building.getDevice("clight-1")` zwraca `DevicePrx` — proxy bazowego interfejsu. Klient nie wie, czy to `Light`, `ColorLight`, `Thermostat` czy `Camera`.

Rozwiązanie: **checkedCast** pyta serwera "czy implementujesz X?":

```python
def cast_to_concrete(base: smarthome.DevicePrx):
    # Próbujemy od najbardziej szczegółowego (ColorLight) w górę (Device)
    cl = smarthome.ColorLightPrx.checkedCast(base)
    if cl is not None:
        return "ColorLight", cl    # serwer powiedział TAK
    li = smarthome.LightPrx.checkedCast(base)
    if li is not None:
        return "Light", li
    # itd...
```

**Dlaczego od najbardziej szczegółowego?** `ColorLight` dziedziczy po `Light`. Gdybyśmy najpierw pytali `LightPrx.checkedCast`, `clight-1` odpowiedziałby TAK (bo implementuje Light) — ale stracilibyśmy dostęp do `setColor`/`getColor`. Zawsze zaczynamy od liścia hierarchii.

Każdy `checkedCast` to **osobny request sieciowy** (ice_isA). Dla klienta interaktywnego to akceptowalne.

### 5.4 Jak wywołuje się zdalne metody w Pythonie

```python
# prx to np. ColorLightPrx
prx.setColor(smarthome.Color(255, 0, 0))
# ↑ wygląda jak lokalne wywołanie, ale:
# 1) stub serializuje Color(255,0,0) do bajtów Ice
# 2) wysyła przez TCP do serwera
# 3) serwer wywołuje colorLightI.setColor(Color(255,0,0), current)
# 4) odpowiedź (void) wraca przez TCP
# 5) metoda wraca
```

Struktury są zwykłymi obiektami Pythona:
```python
c = smarthome.Color(r=255, g=0, b=0)  # lub Color(255, 0, 0)
prx.setColor(c)
p = smarthome.PTZ(pan=45.0, tilt=-10.0, zoom=2)
prx.setPTZ(p)
```

Enumy:
```python
smarthome.PowerState.On    # odpowiednik Java: PowerState.On
smarthome.HvacMode.Heating
```

---

## 6. gRPC — teoria

### 6.1 Czym różni się od Ice

| | ZeroC Ice | gRPC |
|---|---|---|
| Protokół | Własny binarny (Ice protocol) | HTTP/2 |
| IDL | Slice (.ice) | Protocol Buffers (.proto) |
| Obiekty | Identity-based (każde urządzenie = osobny obiekt) | Service-based (jedna usługa obsługuje wiele urządzeń) |
| Streaming | Nie (w podstawowej wersji) | Tak (4 tryby) |
| Reflection | Opcjonalna (osobna biblioteka) | Wbudowana (grpc-services) |

### 6.2 HTTP/2 pod spodem

gRPC korzysta z **HTTP/2** — co daje:
- **Multiplexing**: wiele RPC przez jeden socket TCP jednocześnie (bez head-of-line blocking jak w HTTP/1.1)
- **Header compression** (HPACK)
- **Full-duplex streaming** — serwer może wysyłać wiadomości bez czekania na request klienta

### 6.3 Cztery tryby RPC w gRPC

| Tryb | Definicja w proto | Opis |
|------|------------------|------|
| Unary | `rpc Method(Req) returns (Resp)` | klasyczne request/response |
| Server streaming | `rpc Method(Req) returns (stream Resp)` | jedno żądanie, wiele odpowiedzi |
| Client streaming | `rpc Method(stream Req) returns (Resp)` | wiele żądań, jedna odpowiedź |
| Bidirectional | `rpc Method(stream Req) returns (stream Resp)` | pełny duplex |

W projekcie używamy **unary** (ListDevices, SetMode) i **server streaming** (StreamReadings).

### 6.4 Stub vs. Service vs. Channel

```
Channel ─────────── połączenie HTTP/2 z serwerem
    │
    ├── Stub ──────── "fasada" do wywoływania metod (generowany przez protoc)
    │                 DeviceServiceGrpc.DeviceServiceStub (klient)
    │                 DeviceServiceGrpc.DeviceServiceImplBase (serwer, abstract)
    │
    └── (opcjonalnie) Server Reflection ─── meta-usługa opisująca inne usługi
```

### 6.5 Status codes w gRPC zamiast wyjątków

gRPC nie ma wyjątków IDL jak Ice. Zamiast tego każde RPC zwraca **Status code**:

| Status | Znaczenie | Kiedy użyć |
|--------|-----------|-----------|
| `OK` | Sukces | zawsze gdy wszystko OK |
| `NOT_FOUND` | Obiekt nie istnieje | nieznane deviceId |
| `INVALID_ARGUMENT` | Zły parametr | zły typ urządzenia dla setMode |
| `CANCELLED` | Anulowano | przerwanie streamingu |
| `INTERNAL` | Błąd serwera | nieoczekiwany wyjątek |

Po stronie serwera Java:
```java
resp.onError(Status.NOT_FOUND
    .withDescription("device not found: " + req.getDeviceId())
    .asRuntimeException());
```

Po stronie klienta Python:
```python
except grpc.RpcError as ex:
    print(f"code={ex.code().name} details={ex.details()}")
    # → code=NOT_FOUND details='device not found: no-such-id'
```

### 6.6 Server Reflection — kluczowe dla I1

**Server Reflection** to specjalna meta-usługa (`grpc.reflection.v1alpha.ServerReflection`) wbudowana w serwer. Pozwala klientowi:
1. Zapytać "jakie usługi tu są?" → lista serwisów
2. Zapytać "pokaż mi FileDescriptorProto dla usługi X" → bajty z opisem struktury

`FileDescriptorProto` to skompilowany binarnie opis pliku `.proto` — zawiera informacje o wszystkich typach, metodach, polach.

**Dzięki reflection:** `grpcurl`, Postman i nasz `grpc_dyn_client.py` mogą działać **bez dostępu do pliku .proto w czasie kompilacji**. Pobierają opis usługi w runtime.

Po stronie serwera Java wystarczy jedna linia:
```java
ServerBuilder.forPort(50051)
    .addService(new DeviceServiceImpl())
    .addService(ProtoReflectionService.newInstance())  // ← KLUCZOWE
    .build();
```

---

## 7. Protobuf IDL

### 7.1 Podstawowa składnia `.proto`

```proto
syntax = "proto3";          // wersja (zawsze proto3 w nowych projektach)
package smarthome.dyn;      // przestrzeń nazw (wpływa na pełne nazwy typów)

option java_package = "smarthome.grpc.proto";  // pakiet Java dla generowanych klas
option java_multiple_files = true;             // jedna klasa = jeden plik .java

service DeviceService {
    rpc ListDevices (ListRequest) returns (DeviceList);          // unary
    rpc StreamReadings (StreamRequest) returns (stream Reading); // server-streaming
}

message ListRequest {
    string kindFilter = 1;  // pole o numerze 1 (numer ≠ wartość, to tag serializacji)
}
```

### 7.2 Numery pól w proto3

```proto
message DeviceStatus {
    string id   = 1;
    string kind = 2;
    bool   on   = 3;
    map<string, string> attributes = 4;
}
```

Liczby (1, 2, 3...) to **tagi serializacji**, nie wartości. Protobuf koduje dane jako pary `(tag, wartość)`. Dzięki temu:
- Można dodawać pola nie łamiąc kompatybilności wstecznej (stary klient po prostu ignoruje nieznane tagi)
- Brakujące pola = wartości domyślne (string → "", int → 0, bool → false)

**Ważne:** Raz przypisanego tagu nigdy nie zmieniaj (złamie kompatybilność binarną).

### 7.3 Typy złożone w proto3

```proto
repeated DeviceStatus devices = 1;     // lista (jak List<DeviceStatus> w Javie)
map<string, string> attributes = 4;    // mapa stringów
enum Mode { OFF = 0; HEATING = 1; }   // enum (wartość 0 musi być DEFAULT)
```

**Dlaczego `enum Mode` ma wartość 0?** Proto3 wymaga żeby wartość domyślna była 0. Przy deserializacji pola o wartości 0 = domyślna. `UNRECOGNIZED` generowane jest automatycznie jako fallback.

### 7.4 Co generuje `protoc` (przez Maven)

Z `smarthome.proto`:
- `DeviceStatus.java`, `ListRequest.java` itd. — klasy wiadomości z builderem
- `DeviceServiceGrpc.java` — zawiera:
  - `DeviceServiceGrpc.DeviceServiceImplBase` — klasa abstrakcyjna do implementacji serwera
  - `DeviceServiceGrpc.DeviceServiceStub` — klasa proxy dla klienta

Trafia do: `server-java/target/generated-sources/protobuf/`

---

## 8. Serwer gRPC (Java)

### 8.1 `GrpcServerApp` — start serwera

```java
Server server = ServerBuilder.forPort(50051)
    .addService(new DeviceServiceImpl())
    .addService(ProtoReflectionService.newInstance())
    .build()
    .start();
server.awaitTermination();
```

`ProtoReflectionService.newInstance()` automatycznie rejestruje opisy wszystkich usług dodanych do buildera. Klienci mogą je odpytywać przez reflection API.

### 8.2 `DeviceServiceImpl` — implementacja unary

```java
@Override
public void listDevices(ListRequest req, StreamObserver<DeviceList> resp) {
    // req  = to co przysłał klient (ListRequest z polem kindFilter)
    // resp = "kanał" do odesłania odpowiedzi

    DeviceList.Builder out = DeviceList.newBuilder();
    // ... dodaj urządzenia do out ...
    resp.onNext(out.build());   // wyślij ONE odpowiedź
    resp.onCompleted();          // zamknij stream (koniec unary)
}
```

Dla **unary**: zawsze dokładnie jedno `onNext()` + `onCompleted()`.

### 8.3 `DeviceServiceImpl` — implementacja server-streaming

```java
@Override
public void streamReadings(StreamRequest req, StreamObserver<Reading> resp) {
    for (int i = 0; i < n; i++) {
        Reading r = Reading.newBuilder()
            .setDeviceId(req.getDeviceId())
            .setValue(20.0 + rng.nextDouble() * 5.0)
            .setTimestampMs(System.currentTimeMillis())
            .build();
        resp.onNext(r);              // wyślij i-tą wiadomość
        Thread.sleep(intervalMs);    // poczekaj między odczytami
    }
    resp.onCompleted();              // po wysłaniu wszystkich: zamknij
}
```

Dla **server-streaming**: wiele `onNext()` → jeden `onCompleted()`. Klient iteruje przez odpowiedzi jak przez listę.

### 8.4 Błąd zamiast odpowiedzi

```java
if (ref == null) {
    resp.onError(Status.NOT_FOUND
        .withDescription("device not found: " + req.getDeviceId())
        .asRuntimeException());
    return;  // ← WAŻNE: po onError() nie wołamy onCompleted() !
}
```

`onError()` i `onCompleted()` wzajemnie się wykluczają — wywołanie któregokolwiek zamyka stream.

---

## 9. Wywołanie dynamiczne

To jest **sedno zadania I1**. Zrozum to dokładnie.

### 9.1 Co to jest wywołanie dynamiczne i po co

**Statyczne** wywołanie (normalne): masz skompilowane stuby `*_pb2.py` lub `DeviceServiceGrpc.java`. Kompilator IDL wygenerował klasy — znasz typy wiadomości, metody itp. **w czasie kompilacji**.

**Dynamiczne** wywołanie: **nie masz stubów**. Dowiadujesz się co serwer oferuje **w czasie wykonania** (runtime). Piszesz kod, który potrafi wywoływać dowolną metodę na dowolnej usłudze gRPC — bez uprzedniej kompilacji `.proto`.

**Po co to?**
- Narzędzia diagnostyczne: `grpcurl`, Postman — nie znają Twoich proto w czasie kompilacji
- API gateways
- Serwisy testowe, które muszą wywoływać wiele różnych backendów
- Systemy pluginów

### 9.2 Mechanizm krok po kroku

```
grpc_dyn_client.py                     gRPC Server (Java)
─────────────────────────────────────────────────────────
1. Połącz się z localhost:50051
   grpc.insecure_channel("localhost:50051")
   
2. Zapytaj o dostępne usługi                ServerReflection.list_services()
   ──────── reflection request ────────────►
   ◄──── ["grpc.reflection...", "smarthome.dyn.DeviceService"] ────
   
3. Pobierz FileDescriptorProto              ServerReflection.file_containing_symbol
   ──────── reflection request ────────────►
   ◄──── bytes (skompilowany opis .proto) ────────────────────────
   
4. Sparsuj bajty do FileDescriptorProto:
   fd = descriptor_pb2.FileDescriptorProto()
   fd.ParseFromString(bytes)
   
5. Dodaj do puli deskryptorów:
   pool = descriptor_pool.DescriptorPool()
   pool.Add(fd)
   
6. Wyciągnij ServiceDescriptor:
   service = pool.FindServiceByName("smarthome.dyn.DeviceService")
   # service.methods → [ListDevices, SetMode, StreamReadings]
   # method.input_type → deskryptor ListRequest
   # method.output_type → deskryptor DeviceList
   
7. Wygeneruj klasy wiadomości w runtime:
   ListRequestCls = message_factory.GetMessageClass(
       pool.FindMessageTypeByName("smarthome.dyn.ListRequest")
   )
   
8. Stwórz obiekt wiadomości:
   req = ListRequestCls(kindFilter="Light")
   
9. Wywołaj metodę przez channel (bez stuba!):
   rpc = channel.unary_unary(
       "/smarthome.dyn.DeviceService/ListDevices",
       request_serializer=lambda m: m.SerializeToString(),
       response_deserializer=DeviceListCls.FromString
   )
   resp = rpc(req)
```

### 9.3 Klasa `DynamicSchema` — wyjaśnienie linijka po linijce

```python
class DynamicSchema:
    def __init__(self, channel, service_fqn):
        self.pool = descriptor_pool.DescriptorPool()
        # DescriptorPool = kontener na wszystkie "typy" znane w runtime
        # Jak JVM's class registry, ale dla typów protobuf
        
        self._reflection = reflection_pb2_grpc.ServerReflectionStub(channel)
        # ← JEDYNY dozwolony stub — do reflection API, nie nasz IDL!
        
        files = self._fetch_files_for_symbol(service_fqn)
        # Pobiera FileDescriptorProto (bajty opisujące .proto) z serwera
        
        self._add_files_to_pool(files)
        # Dodaje deskryptory do poolu (retry loop na wypadek złej kolejności)
        
        self.service = self.pool.FindServiceByName(service_fqn)
        # Teraz mamy ServiceDescriptor — odpowiednik skompilowanego IDL

    def message_class(self, fqn):
        descriptor = self.pool.FindMessageTypeByName(fqn)
        return message_factory.GetMessageClass(descriptor)
        # GetMessageClass() dynamicznie tworzy klasę Pythona
        # Można ją używać jak normalną: ListRequest(kindFilter="Light")
```

### 9.4 Dlaczego retry loop w `_add_files_to_pool`

FileDescriptorProto może mieć zależności (importowane pliki `.proto`). Jeśli serwer zwróci je w złej kolejności (np. importowany plik po importującym), `pool.Add()` rzuci błąd "zależność nieznana". Retry loop próbuje je dodać wielokrotnie aż wszystkie się dodadzą.

W naszym prostym projekcie (jeden plik `.proto`) nie jest potrzebny, ale jest dobra praktyką dla bardziej złożonych schematów.

### 9.5 `channel.unary_unary()` bez stuba

```python
rpc = channel.unary_unary(
    "/smarthome.dyn.DeviceService/ListDevices",  # path = /package.Service/Method
    request_serializer=lambda msg: msg.SerializeToString(),
    # serializer = jak przetworzyć obiekt na bajty
    response_deserializer=DeviceListCls.FromString,
    # deserializer = jak przetworzyć bajty na obiekt
)
response = rpc(request_object)
```

To dokładnie to samo co robi normalny stub — tylko że normalny stub ma te informacje zakodowane na stałe w generowanym kodzie. My podajemy je dynamicznie.

### 9.6 `channel.unary_stream()` dla streamingu

```python
rpc = channel.unary_stream(
    "/smarthome.dyn.DeviceService/StreamReadings",
    request_serializer=...,
    response_deserializer=ReadingCls.FromString,
)
for reading in rpc(request_object):
    # każde reading to jeden Reading przysłany przez serwer
    print(reading.value, reading.timestampMs)
```

Iterujemy po odpowiedziach — gRPC automatycznie czeka na kolejne wiadomości z HTTP/2 stream.

---

## 10. Klient dynamiczny Python

### 10.1 `cmd_discover()` — jak listujemy usługi

```python
stub = reflection_pb2_grpc.ServerReflectionStub(channel)
req = reflection_pb2.ServerReflectionRequest(list_services="")
for resp in stub.ServerReflectionInfo(iter([req])):
    services = list(resp.list_services_response.service)
    for s in services:
        print(s.name)  # np. "smarthome.dyn.DeviceService"
```

`ServerReflectionInfo` jest samo w sobie bidirectional streaming. Wysyłamy jeden request, dostajemy jedną odpowiedź (tutaj — listę usług).

### 10.2 `cmd_setmode()` — enum dynamicznie

```python
mode_descriptor = schema.pool.FindEnumTypeByName("smarthome.dyn.Mode")
# mode_descriptor.values = [OFF(0), HEATING(1), COOLING(2)]
mode_value = mode_descriptor.values_by_name["HEATING"].number  # → 1
req = SetModeRequest(deviceId="thermo-1", mode=mode_value)
```

Nie używamy `Mode.HEATING` z wygenerowanego kodu — bo go nie mamy! Patrzymy do deskryptora i tłumaczymy nazwy na liczby.

### 10.3 Co oznacza "bez stubów"

Jedyne importy z gRPC/protobuf w `grpc_dyn_client.py`:
```python
import grpc                                              # transport
from google.protobuf import descriptor_pb2              # parsowanie FileDescriptorProto
from google.protobuf import descriptor_pool             # kontener na typy
from google.protobuf import message_factory             # tworzenie klas z deskryptorów
from grpc_reflection.v1alpha import reflection_pb2      # klasy dla reflection API
from grpc_reflection.v1alpha import reflection_pb2_grpc # stub reflection API
```

**NIE ma** `import smarthome_pb2` ani żadnego importu związanego z naszym plikiem `.proto`.

---

## 11. Uruchomienie

### 11.1 Wymagania wstępne (sprawdź przed prezentacją)

```powershell
java --version         # Java 17 lub 21
mvn --version          # 3.8+ (lub ścieżka do Apache Maven)
slice2java --version   # 3.7.11 z C:\Program Files\ZeroC\Ice-3.7.11\bin\
slice2py --version     # 3.7.11
py -3.11 --version     # Python 3.11.x
grpcurl --version      # dowolna wersja
```

Jeśli `mvn` nie jest w PATH:
```powershell
$env:PATH = "$env:LOCALAPPDATA\Apache\apache-maven-3.9.9\bin;$env:PATH"
```

### 11.2 Generacja stubów (raz, przed pierwszym buildem)

```powershell
cd "Lab3&4_middleware\Home Tasks\project"

# Java stubs (Slice → Java)
powershell -ExecutionPolicy Bypass -File .\scripts\gen-slice-java.ps1
# Wynik: server-java/target/generated-sources/slice/smarthome/*.java

# Python stubs (Slice → Python)
powershell -ExecutionPolicy Bypass -File .\scripts\gen-slice-py.ps1
# Wynik: client-python/generated/smarthome_ice.py
```

### 11.3 Build serwera Java

```powershell
cd server-java
mvn -q -DskipTests package
# Wynik: target/server-java-1.0.0-all.jar (~20 MB, uber-jar ze wszystkimi zależnościami)
cd ..
```

Co robi Maven:
1. `os-maven-plugin:detect` — wykrywa OS/architekturę (potrzebne do pobrania `protoc`)
2. `protobuf-maven-plugin:compile` — uruchamia `protoc`, generuje klasy Java z `smarthome.proto` → `target/generated-sources/protobuf/`
3. `build-helper:add-source` — dodaje `target/generated-sources/slice/` do ścieżki kompilacji
4. `compiler:compile` — kompiluje wszystkie 51 plików .java → `target/classes/`
5. `shade:shade` — pakuje wszystko (+ zależności) do `server-java-1.0.0-all.jar`

### 11.4 Setup środowiska Python

```powershell
py -3.11 -m venv client-python\.venv
client-python\.venv\Scripts\Activate.ps1
pip install -r client-python/requirements.txt
```

**Dlaczego Python 3.11, nie 3.13?** `zeroc-ice==3.7.10` nie ma kół (wheels) dla 3.13. Koła muszą być skompilowane dla konkretnej wersji CPython.

### 11.5 Uruchomienie 3 serwerów

Otwórz 3 osobne terminale PowerShell:

**Terminal 1 — Ice serwer building-1 (port 10000):**
```powershell
cd "Lab3&4_middleware\Home Tasks\project\server-java"
java -cp target\server-java-1.0.0-all.jar smarthome.ice.IceServerApp --config config/building-1.properties
```

**Terminal 2 — Ice serwer building-2 (port 10001):**
```powershell
cd "Lab3&4_middleware\Home Tasks\project\server-java"
java -cp target\server-java-1.0.0-all.jar smarthome.ice.IceServerApp --config config/building-2.properties
```

**Terminal 3 — gRPC serwer (port 50051):**
```powershell
cd "Lab3&4_middleware\Home Tasks\project\server-java"
java -cp target\server-java-1.0.0-all.jar smarthome.grpc.GrpcServerApp --port 50051
```

Lub przez skrypty (automatycznie budują jeśli jar nie istnieje):
```powershell
cd "Lab3&4_middleware\Home Tasks\project"
$env:PATH = "$env:LOCALAPPDATA\Apache\apache-maven-3.9.9\bin;$env:PATH"
powershell -ExecutionPolicy Bypass -File .\scripts\run-ice-1.ps1
# analogicznie run-ice-2.ps1 i run-grpc.ps1
```

### 11.6 Uruchomienie klientów

**Terminal 4 — klient Ice (A1):**
```powershell
cd "Lab3&4_middleware\Home Tasks\project\client-python"
.\.venv\Scripts\Activate.ps1
python ice_client.py `
    --proxy "building:tcp -h localhost -p 10000" `
    --proxy "building:tcp -h localhost -p 10001"
```

**Terminal 5 — klient dynamiczny gRPC (I1):**
```powershell
cd "Lab3&4_middleware\Home Tasks\project\client-python"
# (venv aktywowany)
python grpc_dyn_client.py --address localhost:50051
```

### 11.7 grpcurl — komendy do demonstracji

```powershell
# Lista usług
grpcurl -plaintext localhost:50051 list

# Lista metod usługi
grpcurl -plaintext localhost:50051 list smarthome.dyn.DeviceService

# Opis usługi (typy wiadomości)
grpcurl -plaintext localhost:50051 describe smarthome.dyn.DeviceService

# Unary: ListDevices (wszystkie urządzenia)
grpcurl -plaintext -d '{}' localhost:50051 smarthome.dyn.DeviceService/ListDevices

# Unary: ListDevices z filtrem
grpcurl -plaintext -d '{"kindFilter":"Thermostat"}' localhost:50051 smarthome.dyn.DeviceService/ListDevices

# Unary: SetMode
grpcurl -plaintext -d '{"deviceId":"thermo-1","mode":"HEATING"}' localhost:50051 smarthome.dyn.DeviceService/SetMode

# Server-streaming: StreamReadings (5 próbek co 300ms)
grpcurl -plaintext -d '{"deviceId":"thermo-1","samples":5,"intervalMs":300}' localhost:50051 smarthome.dyn.DeviceService/StreamReadings

# Błąd NOT_FOUND
grpcurl -plaintext -d '{"deviceId":"no-such"}' localhost:50051 smarthome.dyn.DeviceService/SetMode

# Błąd INVALID_ARGUMENT (kamera nie ma setMode)
grpcurl -plaintext -d '{"deviceId":"camera-1","mode":"HEATING"}' localhost:50051 smarthome.dyn.DeviceService/SetMode
```

### 11.8 ice_client — komendy do demonstracji

Po uruchomieniu:
```
> l                      ← lista 10 urządzeń z obu serwerów

> d clight-1             ← przejście do ColorLight
clight-1> info           ← DeviceInfo(id, kind, power)
clight-1> color 0 255 0  ← setColor(rgb=0,255,0) — struct jako argument
clight-1> color?         ← getColor()
clight-1> brightness 200 ← → REMOTE InvalidParameter: field='brightness'
clight-1> back

> d thermo-1
thermo-1> mode Heating   ← setMode z enum
thermo-1> target 22.5    ← setTarget z float
thermo-1> target 99      ← → REMOTE InvalidParameter: field='target'
thermo-1> back

> d camera-1
camera-1> ptz 45 10 3    ← setPTZ(struct PTZ)
camera-1> ptz?           ← getPTZ()
camera-1> snapshot       ← (×5) → po 5. REMOTE DeviceUnavailable
camera-1> back

> q                      ← wyjście
```

### 11.9 grpc_dyn_client — komendy do demonstracji

```
grpc-dyn> discover           ← lista usług i metod przez Reflection
grpc-dyn> list               ← ListDevices (wszystkie)
grpc-dyn> list Light         ← ListDevices z kindFilter="Light"
grpc-dyn> setmode thermo-1 COOLING   ← SetMode (unary)
grpc-dyn> setmode thermo-2 HEATING
grpc-dyn> setmode camera-1 HEATING   ← → INVALID_ARGUMENT
grpc-dyn> setmode no-such-id OFF     ← → NOT_FOUND
grpc-dyn> stream thermo-1 5 300      ← StreamReadings (5 odczytów co 300ms)
grpc-dyn> q
```

---

## 12. Decyzje projektowe i ich uzasadnienie

### 12.1 Dlaczego A1 w Ice a I1 w gRPC?

- **Treść A1** mówi o "urządzeniach jako osobnych obiektach" i dostępie przez "Identity" — to dokładnie model Ice. gRPC jest bardziej service-oriented i kłóciłoby się z wymaganiem "każde urządzenie = osobny obiekt".
- **Treść I1** zaleca gRPC z Server Reflection + `grpcurl` — zadanie jest zoptymalizowane pod gRPC.
- Wymóg technologiczny: zestaw musi zawierać gRPC + (Ice lub Thrift). ✓

### 12.2 Dlaczego Java/Python?

- **Java**: dojrzała biblioteka `com.zeroc:ice` z pełnym wsparciem dla Ice 3.7, stabilny `io.grpc`, Maven automatyzuje wszystko.
- **Python**: czytelny kod klienta, zeroc-ice 3.7.10 ma koła dla 3.11, grpcio ma pełne API do dynamicznych wywołań.
- Dwa różne języki = spełnienie wymagania "klient i serwer w różnych językach". ✓

### 12.3 Dlaczego hierarchia urządzeń (`BaseDeviceI` → `LightI` → `ColorLightI`)?

- Zadanie wymaga co najmniej 1-2 typów z podtypami.
- `ColorLight` rozszerza `Light` — unika duplikacji (brightness jest we wszystkich lampach).
- Odpowiada hierarchii w IDL — `ColorLight extends Light extends Device`.
- Czytelna demonstracja na prezentacji: "mamy 3-poziomowe dziedziczenie w IDL, które przekłada się 1:1 na hierarchię klas Javy".

### 12.4 Dlaczego `Building` ma `getDevice(id)` zamiast osobnych proxy?

Alternatywa: klient buduje proxy string `"light-1:tcp -h localhost -p 10000"` sam.
Problem: klient musiałby znać port każdego serwera i konstruować stringi proxy ręcznie.
Nasze podejście: klient zna tylko `building:tcp -h localhost -p 10000`, pyta `getDevice("light-1")` i dostaje gotowy proxy. Bardziej obiektowe, serwer jest single source of truth dla adresów obiektów.

### 12.5 Dlaczego 2 osobne procesy serwerowe Ice?

Wymóg z treści A1: "demonstracja na co najmniej dwóch [procesach]". Nie ma żadnej dodatkowej logiki koordynacyjnej między nimi — są całkowicie niezależne. Klient łączy się z oboma przez dwa różne `--proxy` argumenty.

### 12.6 Dlaczego snapshot rzuca wyjątek po 5. wywołaniu?

`DeviceUnavailable` musi być *demonstrowalny* na prezentacji. Kamerka "przegrzewająca się po 5 zdjęciach" jest naturalną metaforą sprzętowej awarii. Prowadzący może zobaczyć: 4 udane snapshoty → 5. rzuca `DeviceUnavailable` z opisem.

### 12.7 Dlaczego `map<string,string>` w `DeviceStatus` gRPC?

Urządzenia mają różne atrybuty (brightness, color, target, mode, PTZ). Zamiast 4 osobnych typów wiadomości, jedna elastyczna mapa. Spełnia wymóg "nietrywialnych typów danych" i czyni listę urządzeń czytelną w jednym typie wiadomości.

### 12.8 Dlaczego `idempotent` na `info()`, `getTarget()` itd.?

Te metody tylko odczytują stan — wywołanie ich wielokrotnie z tymi samymi parametrami = ten sam wynik. Oznaczenie `idempotent` pozwala Ice na automatyczny retry przy błędach sieciowych, co zwiększa niezawodność w środowiskach NAT/PAT (wymaganie z "Uwag wspólnych").

### 12.9 Dlaczego `setPTZ(PTZ struct)` zamiast `setPan(float) + setTilt(float) + setZoom(int)`?

Wymaganie z treści: "operacje wykraczające poza get/set". `setPTZ(struct)` ustawia cały stan kamery w jednym wywołaniu — bardziej efektywne (1 round-trip zamiast 3), bardziej atomowe (nie ma stanu pośredniego gdzie pan=45 ale zoom jeszcze stary). Możliwość uzasadnienia "efektywność komunikacji" jak wymagane.

---

## 13. USER FLOW — co musisz umieć zrobić i wiedzieć

### 🔷 Blok 1: Uruchomienie (5 minut przed prezentacją)

- [ ] Otworzyć 5 okien terminalu (2× Ice server, 1× gRPC server, 1× klient Ice, 1× klient gRPC)
- [ ] Aktywować venv (`client-python\.venv\Scripts\Activate.ps1`)
- [ ] Uruchomić oba serwery Ice i sprawdzić czy wypisały "is up"
- [ ] Uruchomić gRPC serwer i sprawdzić czy wypisał "is up"
- [ ] Szybko przetestować że klient Ice łączy i `list` działa

---

### 🔷 Blok 2: Co powiedzieć o IDL

**Slice (`smarthome.ice`):**
- "Mamy 2 enumy: `PowerState` (Off/On) i `HvacMode` (ModeOff/Heating/Cooling)"
- "3 struktury: `Color` (RGB), `PTZ` (pan/tilt/zoom), `DeviceInfo` (id/kind/power)"
- "1 sekwencja: `DeviceInfoSeq` — lista struktury `DeviceInfo`"
- "Dziedziczenie interfejsów: `ColorLight extends Light extends Device` — 3 poziomy"
- "Dziedziczenie wyjątków: `InvalidParameter extends DeviceError` i `DeviceUnavailable extends DeviceError` — wszystkie wyjątki mają wspólną bazę z `reason`"
- "Metoda `Building.getDevice()` zwraca `Device*` — proxy do obiektu Ice"
- "Oznaczenie `idempotent` na odczytach — Ice może je automatycznie ponawiać"

**Proto (`smarthome.proto`):**
- "3 metody: `ListDevices` (unary), `SetMode` (unary), `StreamReadings` (server-streaming)"
- "Słowo `stream` przed typem zwracanym = server-streaming"
- "Typ `DeviceStatus` używa `map<string,string>` — to nietrywialny typ złożony"
- "Enum `Mode` z wartością 0 = domyślna (wymóg proto3)"
- "Numery pól (=1, =2...) to tagi serializacji — nie wartości"

---

### 🔷 Blok 3: Co powiedzieć o serwerze Ice

- "Każde urządzenie to osobny servant zarejestrowany pod własną Identity w `ObjectAdapter`"
- "Identity `light-1` + endpoint `tcp -p 10000` = pełny adres obiektu"
- "Klient nigdy nie łączy się bezpośrednio z urządzeniem — najpierw z `Building` (identity=`building`), który zwraca proxy do urządzenia"
- "Pula wątków (4-8) — Ice obsługuje równoległe wywołania od różnych klientów"
- "Wyjątki są serializowane przez Ice i podróżują przez sieć jak wartości"

---

### 🔷 Blok 4: Co powiedzieć o checkedCast

- "Po stronie klienta Python: dostaję `DevicePrx` — bazowy proxy bez informacji o podtypie"
- "Wywołuję `ColorLightPrx.checkedCast(base)` — to wysyła request `ice_isA(\"::smarthome::ColorLight\")` do serwera"
- "Serwer odpowiada swoją listą `ice_ids` — jeśli zawiera ten typ, zwraca odpowiednio rzutowany proxy"
- "Sprawdzam od najbardziej szczegółowego (ColorLight) do najbardziej ogólnego (Device) — inaczej straciłbym dostęp do metod podtypu"

---

### 🔷 Blok 5: Co powiedzieć o wywołaniu dynamicznym

- "Klient Python nie ma żadnych skompilowanych plików `*_pb2.py` z naszego `smarthome.proto`"
- "Zamiast tego: łączy się z serwerem przez protokół Server Reflection — to wbudowana meta-usługa gRPC"
- "Reflection zwraca `FileDescriptorProto` — bajty opisujące schemat usługi"
- "Parsujemy to przez `descriptor_pb2`, wrzucamy do `DescriptorPool`, dostajemy `ServiceDescriptor`"
- "Z deskryptora tworzymy klasy wiadomości w pamięci przez `message_factory.GetMessageClass()`"
- "Wywołujemy przez `channel.unary_unary()` i `channel.unary_stream()` z ręcznie podanymi serializerami"
- "To dokładnie ten sam mechanizm co `grpcurl` i Postman — nasz klient jest z nimi funkcjonalnie równoważny"

---

### 🔷 Blok 6: Co powiedzieć o strukturze katalogów

- "Generowane pliki (stuby) są w osobnych katalogach: `target/generated-sources/` (Java) i `client-python/generated/` (Python)"
- "Pliki `.class` są w `target/classes/`"
- "Nic wygenerowanego nie miesza się z ręcznie pisanym kodem — zgodnie z 'Uwagami wspólnymi'"

---

### 🔷 Blok 7: Pytania których możesz się spodziewać

**Q: Co się stanie jeśli wyłączysz jeden z serwerów Ice w trakcie działania klienta?**
A: Przy próbie wywołania metody na urządzeniu z tego serwera, Ice rzuci `Ice.ConnectionRefusedException` lub `Ice.ConnectFailedException`. Klient obsługuje to przez `except Ice.LocalException`.

**Q: Czym różni się `ice_ids()` od `ice_isA()`?**
A: `ice_ids()` zwraca listę wszystkich interfejsów implementowanych przez obiekt (np. `["::Ice::Object", "::smarthome::Device", "::smarthome::Light", "::smarthome::ColorLight"]`). `ice_isA(type)` to shortcut — odpowiada na pytanie "czy jesteś X?".

**Q: Dlaczego gRPC klient musi się połączyć zanim wywołuje reflection?**
A: Reflection to normalne RPC na usłudze `grpc.reflection.v1alpha.ServerReflection`. Trzeba mieć aktywny kanał gRPC. Kanał w gRPC jest "lazy" — faktyczne TCP handshake może się odłożyć do pierwszego RPC.

**Q: Co to jest protobuf i jak koduje dane?**
A: Protocol Buffers to binarny format serializacji. Każde pole ma numer (tag). Dane kodowane są jako `(tag << 3 | wire_type) + wartość`. Pola nieobecne = wartość domyślna. Wydajniejszy i bardziej kompaktowy niż JSON/XML.

**Q: Co by się stało gdybyś nie dodał `ProtoReflectionService` do serwera gRPC?**
A: Klient dynamiczny rzuciłby błąd "reflection service not available". `grpcurl` nie mógłby wykryć usług. Normalny klient ze stubami działałby nadal (nie potrzebuje reflection).

**Q: Czy klient Ice wiedziałby że Camera nie jest Light?**
A: Tak — `LightPrx.checkedCast(cameraProxy)` zwróciłoby `None`, bo serwer odpowie że jego `ice_ids` nie zawiera `::smarthome::Light`.

**Q: Jak działa pool wątków Ice i co to oznacza dla synchronizacji?**
A: Ice obsługuje każde przychodzące żądanie w osobnym wątku z puli (domyślnie 4-8 wątków). Jeśli dwóch klientów wywoła `setBrightness` jednocześnie na tej samej lampce, dwa wątki będą modyfikować `this.brightness` jednocześnie — race condition. Dlatego metody `*I` mają `synchronized`.

**Q: Co to jest `Current` w parametrach metod serwera Java?**
A: `com.zeroc.Ice.Current` to obiekt z metadanymi żądania: `current.id` (Identity), `current.operation` (nazwa metody), `current.con` (połączenie). W projekcie nie używamy go bezpośrednio, ale Ice wymaga go w sygnaturach.

---

### 🔷 Blok 8: Logi — co pokazać prowadzącemu

Serwer Ice loguje każde wywołanie:
```
[15:58:35][building-1][clight-1] setColor(rgb=0,255,0)
[15:58:35][building-1][clight-1] getColor()
[15:58:35][building-1][clight-1] setBrightness(200)      ← tu serwer rzucił InvalidParameter
```

Serwer gRPC loguje:
```
[16:01:14][grpc] setMode(deviceId=thermo-1 mode=COOLING)
[16:01:15][grpc] streamReadings(deviceId=thermo-1 samples=4 intervalMs=250)
[16:01:15][grpc]   -> reading(#1 value=21.90)
[16:01:15][grpc]   -> reading(#2 value=23.00)
```

Pokaż że logi pojawiają się **w czasie rzeczywistym** gdy klient wywołuje metody — dowód że komunikacja naprawdę się dzieje.

---

### 🔷 Blok 9: Czego NIE mówić / czego unikać

- Nie mów "to jest prosty getter" — każda metoda ma uzasadnienie
- Nie czytaj kodu linijka po linijce — opowiadaj co robi, nie jak jest napisane
- Nie pomijaj wyjątków — to kluczowy element IDL (oceniany)
- Nie zapomnij pokazać `grpcurl` lub Postman (wymagane w I1)
- Nie zapomnij że klient gRPC nie ma `*_pb2` — to jest sedno I1, pokaż brak importu
- Nie uruchamiaj serwera Ice po raz pierwszy podczas prezentacji — zrób to przed
