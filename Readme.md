# Proxy Caching Server

## Requirements

- **Python 3.8 or higher**
- **No external libraries required**

## Starting the Server

Open a terminal, navigate to the project folder, and run:

```bash
python proxy.py
```

## Admin Panel

Open your browser and go to:

```
http://127.0.0.1:9000
```

You will see a login form. Enter the password set in `config.py` (default: `admin123`).

---

## Testing

In a **second terminal**

### Basic request

```bash
curl -v -x http://127.0.0.1:3128 http://example.com/
```

---

### Cache hit and miss

Run the same URL twice:

```bash
curl -s -x http://127.0.0.1:3128 http://example.com/
curl -s -x http://127.0.0.1:3128 http://example.com/
```

### HTTPS tunneling

```bash
curl -v -x http://127.0.0.1:3128 https://example.com/
```

The proxy terminal will show a `CONNECT tunnel` log line. curl receives a valid HTTPS response. Note that HTTPS responses are **not cached** — the proxy forwards encrypted bytes without reading them.

---
