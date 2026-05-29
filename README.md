# diagram-skill

A Claude and Kiro skill that analyses any repository and produces a
[draw.io](https://www.drawio.com) architecture diagram (`Claude.drawio.xml`).

## How it works

Run `/diagram` in any repo. The skill reads the codebase, computes all coordinates
using a small helper script (`layout.py`), and writes the XML in one shot. A
validation pass runs automatically before the file is written to catch overlapping
edges or edges routed through boxes.

`layout.py` requires only `python3` — no packages, no virtual environment.

`/diagram-validate` is available separately if you want to re-check an existing file.

## Structure

```
diagram-skill/
├── claude/
│   ├── agents/
│   │   └── diagram.md          Agent definition (groups both skills)
│   └── skills/
│       ├── diagram/
│       │   ├── SKILL.md        Generate the diagram
│       │   └── layout.py       Coordinate calculator (requires python3 only)
│       └── diagram-validate/
│           └── SKILL.md        Validate an existing diagram
└── kiro/
    ├── agents/
    │   └── diagram.md
    └── skills/
        ├── diagram/
        │   ├── SKILL.md
        │   └── layout.py       (same as claude copy)
        └── diagram-validate/
            └── SKILL.md
```

## Installation

### Claude Code

Copy the skill and its helper script to `~/.claude/commands/`:

```bash
cp claude/skills/diagram/SKILL.md     ~/.claude/commands/diagram.md
cp claude/skills/diagram/layout.py    ~/.claude/commands/diagram_layout.py
cp claude/skills/diagram-validate/SKILL.md ~/.claude/commands/diagram-validate.md
```

Then invoke with `/diagram` or `/diagram-validate` in any Claude Code session.

### Kiro

Copy the skill and helper script into your project:

```bash
cp kiro/skills/diagram/SKILL.md     .kiro/steering/diagram.md
cp kiro/skills/diagram/layout.py    ~/.claude/commands/diagram_layout.py
cp kiro/skills/diagram-validate/SKILL.md .kiro/steering/diagram-validate.md
```

`layout.py` lives at `~/.claude/commands/diagram_layout.py` regardless of IDE — the
SKILL.md references it at that fixed path.

Kiro steering docs are always-active context, so the skill is available as soon as
you open the project.
