# Computer Use Linux — Harness Kurulum Matrisi

> Eski `nexremote` komutu ve `NEXREMOTE_*` değişkenleri geriye uyum için çalışır.

Her harness bir yetenek seviyesine göre en uygun adaptörü kullanır.
Hiçbiri diğerine bağımlı değildir — biri çalışmıyorsa diğeri devrede.

| Harness / İstemci | Adaptör | Kurulum | Not |
|---|---|---|---|
| **Claude Desktop** | MCP | `claude_desktop_config.json`'a `mcpServers.computer-use-linux` ekle | 28 araç + kaynaklar |
| **Claude Code** | Skill + CLI | bu repoyu `~/.claude/skills/`e bağla, `computer-use-linux` PATH'te | `/computer-use-linux` skill'i |
| **Cursor** | MCP | `.cursor/mcp.json` | stdio |
| **Continue / Roo** | MCP | MCP yapılandırması | stdio |
| **Aider** | CLI | `computer-use-linux` PATH'te; ajan komutu çalıştırır | metin |
| **Codex CLI / Gemini CLI** | CLI | shell erişimi yeterli | metin |
| **Özel / proxy'lenmiş CLI** | CLI | `computer-use-linux ...` komutlarını kabukta çalıştır | evrensel |
| **HTTP-tabanlı uzak ajan** | HTTP | `CUL_TOKEN=X computer-use-linux-http --port 8788` veya `deploy/install-service.sh` | stdlib |
| **Tool-calling'siz model** | Metin protokolü | `computer-use-linux-agent --model-cmd "..." --goal "..."` | ajan döngüsü |
| **Görsel model** | CLI + screenshot | `computer-use-linux screenshot /tmp/s.png` | piksel |
| **Başsız sunucu (GUI yok)** | CLI/HTTP (TUI) | sadece `run`/`screen`/`keys` | otomatik |

## MCP yapılandırma örnekleri

**Claude Desktop** (`~/.config/Claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "computer-use-linux": {
      "command": "/home/KULLANICI/bin/computer-use-linux-mcp"
    }
  }
}
```

**Cursor** (`.cursor/mcp.json` proje kökünde):
```json
{ "mcpServers": { "computer-use-linux": { "command": "/home/KULLANICI/bin/computer-use-linux-mcp" } } }
```
Yolu kendi sisteminden al: `command -v computer-use-linux-mcp` (MCP istemcileri `~`'yi açmaz).

## Skill kurulumu (Claude Code / Claude Desktop skills)

```bash
mkdir -p ~/.claude/skills/computer-use-linux
cp computer-use-linux/adapters/skill/computer-use-linux.md ~/.claude/skills/computer-use-linux/SKILL.md
```
Ardından `computer-use-linux` komutu PATH'te olsun (`install.sh` bunu kurar).
Skill, `computer-use-linux` komutlarını ne zaman ve nasıl kullanacağını ajana anlatır.

## Metin protokolü (herhangi bir model)

Model arayüzü evrenseldir: **stdin → prompt, stdout → metin**. Yani:

```bash
# Yerel ollama
computer-use-linux-agent --model-cmd "ollama run qwen2.5" --goal "Firefox'u aç, duckduckgo'ya git"

# simonw/llm
computer-use-linux-agent --model-cmd "llm -m gpt-4o-mini" --goal "..."

# Proxy'lenmiş özel CLI
computer-use-linux-agent --model-cmd "my-internal-llm chat --quiet" --goal "..."

# Sahte/test modeli
computer-use-linux-agent --model-cmd "python3 my_mock.py" --goal "test"
```

Model, yanıtında `computer-use-linux ...` satırları yazar (ister `TOOL:` önekiyle ister
düz); wrapper ilkini çalıştırır, sonucu modele geri besler, `DONE:` görünce
durur. Böylece **tool-calling desteği olmayan modeller bile ajan olur.**

## Ortam değişkenleri

| Değişken | Etki |
|---|---|
| `CUL_BIN` | `install.sh` wrapper dizini (varsayılan `~/bin`) |
| `CUL_TOKEN` / `CUL_TOKEN_FILE` | HTTP adaptörü için Bearer token (veya onu içeren dosya) |
| `PYTHONPATH` | wrapper'lar otomatik ayarlar; elle kullanımda `core/` ekle |
| `CUL_SERVICE` | `0`: CLI arka plan servisini kullanma; `1`: macOS/Windows'ta da aç (Linux'ta varsayılan açık) |
| `CUL_SERVICE_IDLE` | servis bu kadar sn boşta kalınca kapanır (varsayılan 600) |
| `CUL_STRICT` | `1`: ref hızlı yolunu kapat, her eylemde tüm ağacı oku (ikiz öğe denetimi) |
| `CUL_TRACE` | `1`: her adımın süresi stderr'e |
| `CUL_CURSOR_MS` | ajan imlecinin süzülme süresi (varsayılan 80; tık beklemez) |
| `CUL_SETTLE` | `--after` öncesi arayüzün durulma beklemesi, sn (varsayılan 0.15) |
| `CUL_TREE_NODES` / `CUL_TREE_MS` | ağaç okuma bütçesi (varsayılan 5000 düğüm / 10000 ms) |
| `CUL_KWIN_WATCH` | `0`: uzun ömürlü süreçte KWin kalıcı izleyicisini kapat |

## Sorun giderme

| Belirti | Çözüm |
|---|---|
| `computer-use-linux caps` → GUI kapalı | `sudo apt install python3-gi gir1.2-atspi-2.0` |
| `type`/`key`/`click X Y` çalışmıyor | `computer-use-linux setup` → KDE izninde Share; `computer-use-linux caps` portal durumunu gösterir |
| Electron iç butonları görünmüyor | uygulamayı kapatıp `computer-use-linux launch <program>` ile başlat |
| MCP'de araç yok | `pip install mcp`; wrapper `computer-use-linux-mcp` kullan |
| `computer-use-linux: command not found` | `export PATH="$HOME/bin:$PATH"` |
