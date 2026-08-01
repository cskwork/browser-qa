# Install superqa

<details>
<summary><strong>Claude Code</strong></summary>

### Install

```bash
claude plugin marketplace add cskwork/superqa-skill
claude plugin install superqa@superqa
```

Type `/superqa`.

### Verify

```bash
claude plugin list
```

### Update

```bash
claude plugin marketplace update superqa
```

### Uninstall

```bash
claude plugin uninstall superqa
claude plugin marketplace remove superqa
```

</details>

<details>
<summary><strong>Codex</strong></summary>

### Install

```bash
codex plugin marketplace add cskwork/superqa-skill --ref main
codex plugin add superqa@superqa
```

Type `$superqa`.

### Verify

```bash
codex plugin list
```

### Uninstall

```bash
codex plugin remove superqa
codex plugin marketplace remove superqa
```

</details>

<details>
<summary><strong>Gemini CLI</strong></summary>

### Install (extension, always-on)

```bash
gemini extensions install https://github.com/cskwork/superqa-skill
```

### Install (command, opt-in)

```bash
mkdir -p ~/.gemini/commands
curl -fsSL https://raw.githubusercontent.com/cskwork/superqa-skill/main/skills/superqa-skill/agents/gemini.toml \
  -o ~/.gemini/commands/superqa.toml
```

Type `/superqa` in a new session.

### Verify

```bash
gemini extensions list
```

### Uninstall

```bash
gemini extensions uninstall superqa
```

</details>

<details>
<summary><strong>Cursor, OpenCode, Amp, and other agent-skills harnesses</strong></summary>

### Install

```bash
npx skills add cskwork/superqa-skill
npx skills add cskwork/superqa-skill -g
```

Type `/superqa` in a new agent chat.

### Verify

```bash
npx skills list
```

### Update

```bash
npx skills update superqa
```

### Uninstall

```bash
npx skills remove superqa
```

</details>

<details>
<summary><strong>Antigravity (agy)</strong></summary>

### Install

```bash
agy plugin install https://github.com/cskwork/superqa-skill
```

### Verify

```bash
agy plugin list
```

### Uninstall

```bash
agy plugin uninstall superqa
```

</details>
