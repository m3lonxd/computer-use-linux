# NexRemote — Harness Kurulum Matrisi

> Eski `nexremote` komutu takma ad olarak çalışır.

Her harness bir yetenek seviyesine göre en uygun adaptörü kullanır.
Hiçbiri diğerine bağımlı değildir — biri çalışmıyorsa diğeri devrede.

| Harness / İstemci | Adaptör | Kurulum | Not |
|---|---|---|---|
| **Claude Desktop** | MCP | `claude_desktop_config.json`'a `mcpServers.nexremote` ekle | 23 araç + kaynaklar |
| **Claude Code** | Skill + CLI | bu repoyu `~/.claude/skills/`e bağla, `computer-use-linux` PATH'te | `/nexremote` skill'i |
| **Cursor** | MCP | `.cursor/mcp.json` | stdio |
| **Continue / Roo** | MCP | MCP yapılandırması | stdio |
| **Aider** | CLI | `computer-use-linux` PATH'te; ajan komutu çalıştırır | metin |
| **Codex CLI / Gemini CLI** | CLI | shell erişimi yeterli | metin |
| **Özel / proxy'lenmiş CLI** | CLI | `nexremote ...` komutlarını kabukta çalıştır | evrensel |
| **HTTP-tabanlı uzak ajan** | HTTP | `NEXREMOTE_TOKEN=X computer-use-linux-http --port 8788` veya `deploy/install-service.sh` | stdlib |
| **Tool-calling'siz model** | Metin protokolü | `computer-use-linux-agent --model-cmd "..." --goal "..."` | ajan döngüsü |
| **Görsel model** | CLI + screenshot | `computer-use-linux screenshot /tmp/s.png` | piksel |
| **Başsız sunucu (GUI yok)** | CLI/HTTP (TUI) | sadece `run`/`screen`/`keys` | otomatik |

## MCP yapılandırma örnekleri

**Claude Desktop** (`~/.config/Claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "nexremote": {
      "command": "/home/KULLANICI/bin/computer-use-linux-mcp"
    }
  }
}
```

**Cursor** (`.cursor/mcp.json` proje kökünde):
```json
{ "mcpServers": { "nexremote": { "command": "/home/KULLANICI/bin/computer-use-linux-mcp" } } }
```
Yolu kendi sisteminden al: `command -v computer-use-linux-mcp` (MCP istemcileri `~`'yi açmaz).

## Skill kurulumu (Claude Code / Claude Desktop skills)

```bash
mkdir -p ~/.claude/skills/nexremote
cp nexremote/adapters/skill/nexremote.md ~/.claude/skills/nexremote/SKILL.md
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

Model, yanıtında `nexremote ...` satırları yazar (ister `TOOL:` önekiyle ister
düz); wrapper ilkini çalıştırır, sonucu modele geri besler, `DONE:` görünce
durur. Böylece **tool-calling desteği olmayan modeller bile ajan olur.**

## Ortam değişkenleri

| Değişken | Etki |
|---|---|
| `NEXREMOTE_BIN` | `install.sh` wrapper dizini (varsayılan `~/bin`) |
| `NEXREMOTE_TOKEN` / `NEXREMOTE_TOKEN_FILE` | HTTP adaptörü için Bearer token (veya onu içeren dosya) |
| `PYTHONPATH` | wrapper'lar otomatik ayarlar; elle kullanımda `core/` ekle |

## Sorun giderme

| Belirti | Çözüm |
|---|---|
| `computer-use-linux caps` → GUI kapalı | `sudo apt install python3-gi gir1.2-atspi-2.0` |
| `type`/`key`/`click X Y` çalışmıyor | `computer-use-linux setup` → KDE izninde Share; `computer-use-linux caps` portal durumunu gösterir |
| Electron iç butonları görünmüyor | uygulamayı kapatıp `computer-use-linux launch <program>` ile başlat |
| MCP'de araç yok | `pip install mcp`; wrapper `computer-use-linux-mcp` kullan |
| `computer-use-linux: command not found` | `export PATH="$HOME/bin:$PATH"` |
