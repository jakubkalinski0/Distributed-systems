# Zadanie domowe - część 1: Chat przez TCP (Python)

Wymagania:
- Klienci łączą się z serwerem przez TCP
- Serwer odbiera wiadomości od klientów i rozsyła je do **pozostałych** (z nickiem)
- Serwer jest wielowątkowy (każde połączenie ma swój wątek)

## Uruchomienie

### Serwer

```powershell
python server.py --port 9020
```

### Klient #1

```powershell
python client.py --host 127.0.0.1 --port 9020 --nick ala
```

### Klient #2

```powershell
python client.py --host 127.0.0.1 --port 9020 --nick ola
```

## Komendy w kliencie

- wpisz tekst i Enter -> wysyłka po TCP
- `/quit` -> wyjście

