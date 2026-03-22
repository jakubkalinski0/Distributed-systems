# Zadanie domowe — część 2: Chat TCP + dodatkowy kanał UDP (Python)

Wymagania (część 2):
- serwer i każdy klient mają dodatkowy kanał UDP
- serwer UDP słucha na **tym samym porcie co TCP**
- po komendzie `U` klient wysyła wiadomość UDP na serwer, a serwer rozsyła ją UDP do pozostałych klientów

## Uruchomienie (2 klientów na jednym PC)

Na jednym komputerze **nie da się** uruchomić 2 klientów z tym samym `--local-port`, więc ustaw różne porty lokalne.

### Serwer

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
- `U` lub `U <tekst>` → UDP (serwer rozsyła do innych)
- `/quit` → wyjście

