# Lab 5 (RabbitMQ) - Agencje i Przewoźnicy

System pośredniczący w RabbitMQ między agencjami kosmicznymi a przewoźnikami: trzy typy usług (`people`, `cargo`, `satellite`), kolejki per typ na współdzielonym brokerze, powiadomienia zwrotne (potwierdzenia) oraz moduł administratorski (premium) z audytem i broadcastem.

Domyślny scenariusz demo używa agencji `nasa`, `esa` i przewoźników `carrier1`, `carrier2`, ale CLI akceptuje także inne identyfikatory (`[a-z0-9_-]`).

## Schemat topologii (wymóg zadania)

- Edytowalny diagram diagrams.net: [docs/topologia.drawio](docs/topologia.drawio)
- Grafika elektroniczna (SVG): [docs/topologia.drawio.svg](docs/topologia.drawio.svg)

## Wymagania

- Docker (brokera RabbitMQ) lub dostęp do instancji AMQP (`AMQP_URL`)
- Python 3.11+ (zalecane) oraz `pip`

## Uruchomienie brokera

W katalogu projektu:

```powershell
docker compose up -d
```

Panel zarządzania: `http://localhost:15672/` (guest / guest).

Inny broker: przed uruchomieniem skryptów ustaw np. `$env:AMQP_URL='amqp://user:pass@host:5672/'`.

## Instalacja zależności

```powershell
cd "Lab5_RabbitMQ\Home Task"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Scenariusz prezentacji

Uruchamiaj osobny terminal dla każdego procesu. Kolejność dowolna; RabbitMQ ma być dostępny zanim konsumenci ruszą.

### 1. Dwóch Przewoźników

- **carrier1** - ludzie + ładunki (`people,cargo`)
- **carrier2** - ładunki + satelita (`cargo,satellite`)

```powershell
python carrier.py --id carrier1 --services people,cargo
```

```powershell
python carrier.py --id carrier2 --services cargo,satellite
```

Dla kolejki `q.orders.cargo` obaj tworzą **konkurujących konsumentów** (`prefetch_count=1`); jedno zlecenie trafia dokładnie do jednego aktywnego przewoźnika.

### 2. Dwie Agencje

```powershell
python agency.py --slug nasa
```

```powershell
python agency.py --slug esa
```

W CLI agencji: `<usługa> <numer>`, np. `cargo 101`, `satellite 7`, oraz `quit`. Potwierdzenia i komunikaty admina pojawią się w tym samym oknie.

Możesz uruchomić też inną agencję, np. `python agency.py --slug pksa`; jej kolejki zostaną zadeklarowane automatycznie.

### 3. Administrator (premium)

```powershell
python admin.py
```

- Wątek audytu wypisuje kopię publikowanych komunikatów (target exchange i routing key).
- Interakcyjnie: `agencies komunikat`, `carriers komunikat`, `all komunikat`, `quit`.
- Jednorazowy broadcast z konsoli bez `input`:

```powershell
python admin.py --mode agencies --broadcast "Plan kontrolny 09:00"
```

Tryb **`all`** wysyła dwie osobne publikacje (fanout do agencji oraz fanout do przewoźników).

W trybie jednorazowym możesz doprecyzować czas na wydruk audytu przed zamknięciem procesu:

```powershell
python admin.py --mode all --broadcast "Test premium" --audit-wait-seconds 1.0
```

## Struktura kodu

| Plik | Rola |
|------|------|
| [srq/topology.py](srq/topology.py) | Deklaracja exchange'y, kolejek i bindingów |
| [srq/messaging.py](srq/messaging.py) | JSON, walidacja komunikatów i publikacja z kopią na `ex.audit` |
| [agency.py](agency.py) | Zlecenia, odbiór potwierdzeń oraz broadcast admina dla agencji |
| [carrier.py](carrier.py) | Obsługa zleceń, potwierdzenia, broadcast admina dla przewoźników |
| [admin.py](admin.py) | Audyt kolejki `q.audit.admin` oraz wysyłka broadcastów |

Przyjmujemy uproszczoną symulację z zadania: **obsługa zlecenia jest natychmiastowa** (ACK zaraz po wysłaniu potwierdzenia).

## Skrót komunikatów

- **ORDER** - `{ msgType, agencyId, orderNo, service, issuedAt }` -> `ex.orders` z rk `order.<service>`.
- **CONFIRMATION** - `{ ..., carrierId, completedAt }` -> `ex.confirmations` z rk `agency.<slug>`.
- **ADMIN_BROADCAST** - `{ mode, text, sentAt }` -> `ex.admin.agencies` i/lub `ex.admin.carriers` (fanout).

Wiadomości o niepoprawnym formacie (np. błędny JSON, brak wymaganych pól, zły `msgType`) są odrzucane przez konsumenta (`NACK requeue=false`) i logowane z prefiksem `[...] [odrzucone]`.
