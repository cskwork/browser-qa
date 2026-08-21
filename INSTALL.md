# Install superqa

<details>
<summary><strong>Claude Code</strong></summary>

### Install

```bash
claude plugin marketplace add cskwork/browser-qa
claude plugin install browser-qa@browser-qa
```

Type `/browser-qa`.

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
codex plugin marketplace add cskwork/browser-qa --ref main
codex plugin add browser-qa@browser-qa
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
gemini extensions install https://github.com/cskwork/browser-qa
```


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
npx skills add cskwork/browser-qa
npx skills add cskwork/browser-qa -g
```

Type `/browser-qa` in a new agent chat.

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
agy plugin install https://github.com/cskwork/browser-qa
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
