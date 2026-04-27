# Smart Home – A1 (Ice) + I1 (gRPC dynamic invocation)

Projekt zaliczeniowy z laboratorium "Technologie middleware".

- **A1 ("Inteligentne otoczenie")** — ZeroC Ice 3.7, serwer Java, klient Python (CLI).
- **I1 ("Wywołanie dynamiczne")** — gRPC, serwer Java, klient Python **bez stubów** (używa Server Reflection).

Klient i serwer w **różnych** językach (Java/Python). Generowane stuby trafiają do osobnych katalogów (`server-java/target/generated-sources/`, `client-python/generated/`), pliki kompilacji do `target/` i `__pycache__/` — zgodnie z wymogami z "Uwag wspólnych".

## Struktura repozytorium

```
project/
  README.md                # ten plik
  STATEMENT.md             # oświadczenie o samodzielnym wykonaniu
  idl/
    smarthome.ice          # Slice IDL dla A1
    smarthome.proto        # Protobuf IDL dla I1
  scripts/
    gen-slice-java.ps1     # slice2java -> server-java/target/generated-sources/slice
    gen-slice-py.ps1       # slice2py   -> client-python/generated
    run-ice-1.ps1          # uruchamia serwer Ice "building-1" na :10000
    run-ice-2.ps1          # uruchamia serwer Ice "building-2" na :10001
    run-grpc.ps1           # uruchamia serwer gRPC na :50051
  server-java/
    pom.xml
    src/main/java/smarthome/
      domain/              # POJO modelu domenowego
      ice/                 # implementacja serwera Ice (BuildingI, devices/*I)
      grpc/                # implementacja serwera gRPC (DeviceServiceImpl)
    config/
      building-1.properties
      building-2.properties
  client-python/
    requirements.txt
    ice_client.py          # interaktywny klient Ice (REPL)
    grpc_dyn_client.py     # dynamiczny klient gRPC (BEZ stubów)
    generated/             # slice2py output (tylko A1)
```

## Wymagania środowiska (Windows)

- **Java JDK 17 lub 21** — dowolna dystrybucja (np. Temurin); zweryfikuj `java --version`.
- **Apache Maven 3.8+** — w winget nie ma pakietu, więc pobierz binarkę:
  ```powershell
  $v = "3.9.9"
  Invoke-WebRequest -Uri "https://archive.apache.org/dist/maven/maven-3/$v/binaries/apache-maven-$v-bin.zip" -OutFile "$env:TEMP\maven.zip"
  Expand-Archive "$env:TEMP\maven.zip" -DestinationPath "$env:LOCALAPPDATA\Apache" -Force
  $env:PATH = "$env:LOCALAPPDATA\Apache\apache-maven-$v\bin;$env:PATH"
  mvn --version
  ```
  Aby utrwalić PATH dodaj `$env:LOCALAPPDATA\Apache\apache-maven-3.9.9\bin` w System Properties → Environment Variables → User PATH.
- **ZeroC Ice 3.7.x** — [installer ze strony ZeroC](https://zeroc.com/downloads/ice) (dostarcza `slice2java`, `slice2py`). Skrypty `gen-slice-*.ps1` automatycznie wykrywają instalację w `C:\Program Files\ZeroC\Ice-3.7.11\`.
- **Python 3.11** — `winget install Python.Python.3.11`. **Konieczne**, bo `zeroc-ice` 3.7.10 nie ma wheeli dla Python 3.13.
- **grpcurl** (opcjonalnie, do demonstracji równoważności narzędzi):
  ```powershell
  winget install --id fullstorydev.grpcurl -e
  ```

## Setup krok po kroku

```powershell
cd "Lab3&4_middleware/Home Tasks/project"

# 1) Wygeneruj stuby Slice (Java + Python)
./scripts/gen-slice-java.ps1
./scripts/gen-slice-py.ps1

# 2) Zbuduj serwer Java (Ice + gRPC w jednym module)
cd server-java
mvn -q -DskipTests package
cd ..

# 3) Zainstaluj zależności klienta Python (zalecany Python 3.11)
py -3.11 -m venv client-python/.venv
client-python/.venv/Scripts/Activate.ps1
pip install -r client-python/requirements.txt
deactivate
```

## Uruchomienie demo

W trzech osobnych terminalach:

```powershell
# Terminal 1: Ice server #1 (building-1, port 10000)
./scripts/run-ice-1.ps1

# Terminal 2: Ice server #2 (building-2, port 10001)
./scripts/run-ice-2.ps1

# Terminal 3: gRPC server (port 50051) - z włączonym ServerReflection
./scripts/run-grpc.ps1
```

W czwartym terminalu — klienci:

```powershell
client-python/.venv/Scripts/Activate.ps1

# Klient A1 (Ice) — łączy się z oboma serwerami
python client-python/ice_client.py `
  --proxy "building:tcp -h localhost -p 10000" `
  --proxy "building:tcp -h localhost -p 10001"

# Klient I1 (gRPC) — bez stubów, używa Server Reflection
python client-python/grpc_dyn_client.py --address localhost:50051
```

Demonstracja narzędzi równoważnych dla I1:

```powershell
grpcurl -plaintext localhost:50051 list
grpcurl -plaintext localhost:50051 list smarthome.dyn.DeviceService
grpcurl -plaintext -d '{\"kindFilter\":\"Light\"}' localhost:50051 smarthome.dyn.DeviceService/ListDevices
grpcurl -plaintext -d '{\"deviceId\":\"thermo-1\",\"samples\":5,\"intervalMs\":300}' localhost:50051 smarthome.dyn.DeviceService/StreamReadings
```

## Jak to działa (skrót do obrony)

### A1 / Ice
- Każde urządzenie = osobny obiekt Ice z własną **Identity** (np. `light-1`, `clight-2`, `thermo-1`).
- Klient dostaje proxy `Device*` przez metodę `Building.getDevice(id)` i sprawdza podtyp przez `*Prx.checkedCast(...)`.
- Slice `smarthome.ice` używa: `enum`, `struct`, `sequence`, dziedziczenia interfejsów (`ColorLight extends Light extends Device`), dziedziczenia wyjątków (`InvalidParameter extends DeviceError`), zwracania proxy w wartości metody.
- Walidacja po stronie serwera rzuca `InvalidParameter` / `DeviceUnavailable`, Ice marshaluje wyjątek do klienta.

### I1 / gRPC
- Serwer Java rejestruje **`ProtoReflectionService`** — udostępnia deskryptory `.proto` przez gRPC.
- Klient Python **nie ma żadnych** plików `*_pb2.py` skompilowanych z `smarthome.proto`. W runtime:
  1. Łączy się przez gRPC reflection, pobiera `FileDescriptorProto`.
  2. Buduje `DescriptorPool` z `google.protobuf`.
  3. Generuje klasy wiadomości w pamięci przez `message_factory.GetMessageClass(descriptor)`.
  4. Wywołuje `channel.unary_unary(...)` / `channel.unary_stream(...)` z parą `request_serializer` / `response_deserializer`.
- Ten sam mechanizm wykorzystują `grpcurl` i Postman.

## Skrypt prezentacji (15 min)

1. (1 min) Wstęp — drzewo katalogów w IDE; pokaż `idl/smarthome.ice` i `idl/smarthome.proto`.
2. (2 min) Slice IDL: omów enumy, struktury, sekwencję, dziedziczenie interfejsów (`ColorLight extends Light extends Device`), dziedziczenie wyjątków, zwracanie `Device*` proxy.
3. (1 min) `./scripts/gen-slice-java.ps1` i `./scripts/gen-slice-py.ps1` — pokaż katalogi `target/generated-sources/slice/` i `client-python/generated/` (rozdział od źródeł).
4. (4 min) **A1 demo (Ice)**: w 2 terminalach `./scripts/run-ice-1.ps1` i `./scripts/run-ice-2.ps1`. W 3. terminalu klient z dwoma `--proxy`. Wykonaj:
   - `list` (10 urządzeń),
   - `d clight-1` → `info`, `color 0 255 0`, `color?`, `brightness 200` → `InvalidParameter(field=brightness)`,
   - `d thermo-1` → `mode Heating`, `target 22.5`, `target?`, `target 99` → `InvalidParameter(field=target)`,
   - `d camera-1` → `setPTZ 45 10 3`, 5× `snapshot` → 5. raz `DeviceUnavailable`.
5. (1 min) Pokaż logi `[building-1][light-1] info()` itp. — każde wywołanie zalogowane.
6. (1 min) Otwórz `idl/smarthome.proto`. Uruchom `./scripts/run-grpc.ps1`.
7. (3 min) **I1 demo (gRPC dynamic)**: `python grpc_dyn_client.py`:
   - `discover` — pokazuje listę usług + metod odkrytych przez Reflection,
   - `list` (unary) → wynik z `attributes` jako mapą,
   - `setmode thermo-1 COOLING` (unary, enum dynamicznie),
   - `stream thermo-1 4 250` (server-streaming).
8. (1 min) Drugi terminal: `grpcurl -plaintext localhost:50051 list`, `... ListDevices`, `... StreamReadings`. Wspomnij Postman jako alternatywę.
9. (1 min) Pokaż kod `grpc_dyn_client.py` — udowodnij, że nie ma `import smarthome_pb2` (tylko `grpc`, `grpc_reflection`, `descriptor_pool`, `message_factory`).
10. (1 min) Q&A.

## Co wziąć pod uwagę przy obronie

- **Ice ObjectAdapter + Identity**: każde urządzenie ma własny servant zarejestrowany pod identity. `Building.getDevice(id)` zwraca proxy zbudowane z `adapter.createProxy(id)`.
- **`Prx.checkedCast`**: klient pobiera proxy bazowe (`Device*`) i przez `LightPrx.checkedCast(...)` zapytuje serwer "czy to Light?". Serwer odpowiada listą `ice_ids`. Asynchroniczny RTT, ale wykonywany raz na operowane urządzenie.
- **gRPC Reflection**: kanał systemowy `grpc.reflection.v1alpha.ServerReflection` udostępnia `FileDescriptorProto` plików `.proto` zarejestrowanych w serwerze. Klient parsuje je do `DescriptorPool`, a `MessageFactory` wytwarza klasy wiadomości w runtime. `grpcurl` i Postman używają tej samej procedury — nasz klient Python jest funkcjonalnie równoważny.
- **Stream**: w gRPC HTTP/2 pojedyncze wywołanie RPC może przesłać sekwencję wiadomości w jednym kierunku (server-streaming). U nas `StreamReadings` wysyła `samples` razy `Reading` co `intervalMs`.

## Czeklista przed oddaniem

- [x] Oba serwery Ice startują z 2 różnych configów na 2 portach (10000, 10001).
- [x] Klient Python listuje 10 urządzeń z obu serwerów.
- [x] Każdy typ urządzenia ma demonstrowalną operację z nietrywialnym typem (struct/enum).
- [x] Każdy typ wyjątku jest demonstrowalny (DeviceError, InvalidParameter, DeviceUnavailable).
- [x] Slice + slice2java + slice2py poprawnie generują się ze skryptów.
- [x] Serwer gRPC eksponuje Reflection (`grpcurl ... list` zwraca usługi).
- [x] Klient Python I1 nie importuje żadnego `*_pb2` z `smarthome.proto`.
- [x] Klient I1 ma działające: `discover`, `list`, `setmode`, `stream`.
- [x] `grpcurl` wykonuje wywołanie streamingowe.
- [x] `STATEMENT.md` i `README.md` obecne.
