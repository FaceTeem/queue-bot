# 🤖 Telegram Bot - Status Izvještaja

**Datum:** 2026-11-03  
**Stanje:** ✅ Razvojni setup kompletan - ready za live testiranje

---

## ✅ Što je završeno

### 1. **Kiksevi programskog koda (3/3)**
- [x] **Baž #1:** ADMIN_ID parsing → Sigurna konverzija u `config.py` (non-number → 0)
- [x] **Baž #2:** BOT_TOKEN validation → Premješteno u `main()` (nije više na razini modula)
- [x] **Baž #3:** Datume markirane kao „videne" bez pretplatnika → Provjeravamo pretplatnike PRIJE `is_new()`

### 2. **Poboljšanja**
- [x] Added `.gitignore` - `.env`, `bot.db`, venv, Python cache...
- [x] Added `/status` command - za buduće prikaza podataka
- [x] Error handling za blokirane korisnike (`TelegramForbiddenError`)
- [x] Improved `/start` help tekst

### 3. **Okruženje**
- [x] Virtual environment (venv)
- [x] Sve dependencije instalirane (aiogram, aiohttp, aiosqlite, python-dotenv)
- [x] `.env` datoteka za testiranje (demo mode)
- [x] SQLite baza inicijalizirana

### 4. **Testiranje**
- [x] Syntax check - sve datoteke se kompajliraju bez greške
- [x] Import test - svi moduli se učitavaju ispravno
- [x] Config test - ADMIN_ID parsing radi sa sigurnostom
- [x] Demo fetcher - generiše demo podatke
- [x] Database test - add_sub, user_subs, is_new() rade ispravno
- [x] Checker logika - provjereno bez Telegram konekcije

---

## 📊 Struktura projekta

```
Videos/
├── CLAUDE.md              ← Handoff dokumentacija
├── STATUS.md              ← Ovaj dokument
├── bot.py                 ← Glavni bot (aiogram dispatcher + checker)
├── config.py              ← Konfiguracija (safe ADMIN_ID parsing)
├── db.py                  ← SQLite operacije (subs, seen dates)
├── fetcher.py             ← Demo/live data fetcher
├── requirements.txt       ← Dependencije
├── .env                   ← Konfiguracija (TEST - DON'T COMMIT)
├── .env.example           ← Template za .env
├── .gitignore             ← Git ignore rules
└── README.md              ← Korisničke instrukcije
```

---

## 🚀 Što dalje?

### Phase 1: Live testiranje sa realnim tokenom
```bash
source venv/Scripts/activate
# Dodaj pravi BOT_TOKEN u .env
python bot.py
```

### Phase 2: Pronalazak realnog API-ja
1. Otvori sайt DP "Dokument" u Chrome + DevTools
2. Network tab → Fetch/XHR filter
3. Pronađi zahtjev sa voljnim datama u response-u
4. Kopiraj URL → SLOTS_URL u .env
5. Prilagodi `parse_response()` na stvarnu JSON strukturu

### Phase 3: Live mode
```bash
MODE=live python bot.py
```

### Phase 4: Napredne funkcionalnosti (za kasnije)
- [ ] `/cookie <value>` admin komanda za ažuriranje sesije
- [ ] Praćenje "trenutnog stanja" (otvoreno/zatvoreno)
- [ ] Backoff na SessionExpired (429 retry)
- [ ] Docker image za 24/7 hosting
- [ ] Unit testovi
- [ ] Stalni logovi

---

## 📋 Konfiguracijski parametri

| Varijabla | Obavezna | Default | Opis |
|---|---|---|---|
| `BOT_TOKEN` | DA | — | Token od @BotFather |
| `ADMIN_ID` | NE | 0 | Telegram ID za notifikacije |
| `CHECK_INTERVAL` | NE | 180 | Sekunde između provjera (min 120) |
| `MODE` | NE | demo | `demo` ili `live` |
| `SLOTS_URL` | Za live | — | API endpoint sa voljnim datama |
| `SESSION_COOKIE` | Za live* | — | Cookie header za autentifikaciju |
| `AUTH_HEADER` | Za live* | — | Authorization header ako je potreban |
| `DB_PATH` | NE | bot.db | Putanja do SQLite baze |

---

## 🔍 Kako se bot pokreće

```bash
# 1. Aktiviraj venv
source venv/Scripts/activate  # Linux/macOS
venv\Scripts\activate.bat      # Windows CMD
venv\Scripts\activate          # Windows PowerShell

# 2. Pokrenui bot
python bot.py

# Bot će:
# - Inicijalizirati SQLite bazu
# - Pokrenuti Telegram polling
# - Sve 30s (CHECK_INTERVAL) provjeravati demo datume
# - Slati notifikacije pretplatnicima
```

---

## 🧪 Komande bota

| Komanda | Opis |
|---|---|
| `/start` | Početna poruka sa opisom |
| `/subscribe` | Inline menu za odabir grada + usluge |
| `/my` | Lista trenutnih pretplata |
| `/status` | Potreni status (demo mode info) |
| `/stop` | Uklanja sve pretplate |

---

## ✔️ Checklist prije produkcije

- [ ] Pronađi pravi SLOTS_URL
- [ ] Testiraj sa stvarnim BOT_TOKEN-om
- [ ] Prilagodi `parse_response()` na stvarnu strukturu
- [ ] Postavi MODE=live
- [ ] Testiraj sa stvarnim korisnicima (mali krug)
- [ ] Dodaj Dockerfile / systemd jedinicu za 24/7
- [ ] Postavi monitoring / logging

---

**Gotovo!** Bot je razvojno gotov i čeka live testiranje. 🎉
