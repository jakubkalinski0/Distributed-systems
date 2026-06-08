# Lab 6 Ray — uruchomienie Tier 1 lokalnie (bez AWS)

## Wymagania

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows) — **zalecane** (Ray jest w obrazie)
- Port **8888** wolny na hoście

### Cursor / VS Code — błąd `No module named 'ray'`

Otwierasz `lab-ray.ipynb` z **lokalnym kernelem** (np. Python 3.13). Ray **nie ma** wheela dla każdej wersji Pythona na Windows — wtedy `pip install ray` się nie uda.

**Rozwiązanie:** uruchom notebook w Dockerze (kroki poniżej), **nie** w wbudowanym kernelu Cursora.

Opcjonalnie lokalnie tylko jeśli masz **Python 3.10–3.12** (64-bit):

```powershell
cd Lab6_ray\for-students
py -3.10 -m pip install -r requirements.txt
py -3.10 -m ipykernel install --user --name ray-lab
```

W Cursorze wybierz kernel **ray-lab** (Python 3.10).

## Kroki

### 1. Uruchom Jupyter w kontenerze z Ray

W PowerShell:

```powershell
cd "c:\Users\Jakub Kalinski\Documents\GitHub\Distributed-systems\Lab6_ray\for-students"
docker compose up -d
docker compose logs -f jupyter
```

Poczekaj na linię z adresem Jupyter (zwykle `http://127.0.0.1:8888/...`).

### 2. Otwórz notebook

- Przeglądarka: **http://localhost:8888**
- Hasło/token: **`raylab`**
- Plik: **`lab-ray.ipynb`**

### 3. Połączenie z Ray — **lokalnie, bez AWS**

W komórce `ray.init` ustaw:

```python
USE_REMOTE_CLUSTER = False
```

**Nie** podawaj `address=RAY_ADDRESS` — wtedy Ray startuje **wewnątrz kontenera** (wiele procesów worker na CPU maszyny).

Po uruchomieniu komórki powinno być m.in.:

```text
Connected — mode: local
```

a **nie** komunikaty autoskalera AWS.

### 4. Uruchom cały notebook

Menu: **Kernel → Restart Kernel and Run All Cells**

Tier 1 to sekcje na końcu:

- **7.1** — merge sort (sekwencyjny vs równoległy)
- **8** — π Monte Carlo

### 5. Zatrzymanie

```powershell
docker compose down
```

W notebooku na końcu: `ray.shutdown()`.

---

## Częste problemy

| Problem | Rozwiązanie |
|--------|-------------|
| Stary link AWS / timeout | `USE_REMOTE_CLUSTER = False` |
| `ModuleNotFoundError: ray` | Uruchamiaj notebook **w Dockerze**, nie lokalnym Pythonie bez Ray |
| Wolne Part 6 (wagi sieci) | Normalne; Tier 1 (Part 7–8) działa osobno |
| Ostrzeżenie `/dev/shm` | W `docker-compose.yaml` jest już `shm_size: 2gb` |

## Dashboard Ray (opcjonalnie)

W trybie lokalnym Ray czasem wypisuje adres dashboardu w logu po `ray.init`. W tym compose **nie** ma wystawionego portu 8265 — do Tier 1 nie jest wymagany.

## Oddanie

Wyślij **`lab-ray.ipynb`** z wykonanymi komórkami Part 7–8 (zachowane outputy) lub eksport PDF/HTML według wymagań prowadzącego.
