# Zadanie domowe — część 3: Chat TCP + UDP + Multicast (Python)

Wymagania (część 3):
- multicast ma być **alternatywą** do UDP przez serwer (komenda `M`)
- multicast wysyła bezpośrednio do wszystkich przez adres grupowy (serwer może, ale nie musi odbierać)

## Uruchomienie (2 klientów na jednym PC)

Uwaga: jak w części 2 — ustaw różne `--local-port` dla każdego klienta.

### Serwer (TCP+UDP)

```powershell
python server.py --bind 0.0.0.0 --port 9020
```

### Klient #1

```powershell
python client.py --host 127.0.0.1 --port 9020 --nick ala --local-port 12001
```

### Klient #2

```powershell
python client.py --host 127.0.0.1 --port 9020 --nick ola --local-port 12002
```

## Komendy w kliencie

- tekst → TCP
- `U` / `U <tekst>` → UDP przez serwer
- `M` / `M <tekst>` → multicast (bez serwera)
- `/quit` → wyjście

## Multicast — parametry

Domyślnie:
- grupa: `239.255.0.1`
- port multicast: taki sam jak `--port` (np. 9020)

Jeśli multicast nie działa na Windows, najczęściej problemem jest firewall lub blokada ruchu multicast w sieci.

