#!/usr/bin/env python3
"""
Batch integration script: add skill_view('SKILLNAME') to all profile SOUL.md files.
 
Usage:
    python3 batch-skill-integration.py --skill gitmark --name "gms/hms"
 
Scans ~/.hermes/SOUL.md + ~/.hermes/profiles/*/SOUL.md
and inserts skill_view('SKILLNAME') if not already present.
"""

import os, sys, argparse

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--skill', required=True, help='Skill name (e.g. gitmark)')
    p.add_argument('--name', default='', help='Display name for description')
    return p.parse_args()

def insert_skill_view(content, skill_name, display_name):
    if f"skill_view('{skill_name}')" in content:
        return None  # already present
    
    lines = content.split('\n')
    display = display_name or skill_name
    
    # Strategy 1: ## Codebase Navigation (insert before first codegraph Load line)
    if '## Codebase Navigation' in content:
        for i, line in enumerate(lines):
            if line.strip().startswith('| - `') and f'`{skill_name}`' in line:
                # Already mentioned in list, just add the load instruction before next section
                for j in range(i+1, min(i+5, len(lines))):
                    if lines[j].strip().startswith('|') and 'Load' in lines[j]:
                        lines.insert(j, f"| Загрузи: `skill_view('{skill_name}')`")
                        return '\n'.join(lines)
                # Fallback: add right after the mention
                lines.insert(i+1, f"| Загрузи: `skill_view('{skill_name}')`")
                return '\n'.join(lines)
        # Codebase Navigation exists but no mention → add after header
        for i, line in enumerate(lines):
            if line.strip() == '## Codebase Navigation':
                insert = i+1
                while insert < len(lines) and not lines[insert].strip().startswith('## '):
                    insert += 1
                lines.insert(insert, f"Загрузи `{skill_name}` — `skill_view('{skill_name}')`. {display}")
                return '\n'.join(lines)
    
    # Strategy 2: Vault frontmatter section
    if '## Vault frontmatter' in content:
        for i, line in enumerate(lines):
            if line.strip().startswith('## Vault frontmatter'):
                lines.insert(i+1, '')
                lines.insert(i+2, f"Загрузи `{skill_name}` — `skill_view('{skill_name}')`. {display}")
                return '\n'.join(lines)
    
    # Strategy 3: Save to Obsidian section
    for marker in ['## Save to Obsidian', '## Сохрани']:
        if marker in content:
            for i, line in enumerate(lines):
                if line.strip().startswith(marker):
                    lines.insert(i+2, '')
                    lines.insert(i+3, f"Загрузи `{skill_name}` — `skill_view('{skill_name}')`. {display}")
                    return '\n'.join(lines)
    
    # Strategy 4: Fallback — insert after first ## header
    for i, line in enumerate(lines):
        if line.strip().startswith('## ') and i > 0:
            lines.insert(i, '')
            lines.insert(i, f"Загрузи `{skill_name}` — `skill_view('{skill_name}')`. {display}")
            return '\n'.join(lines)
    
    return content + f"\n\nЗагрузи `{skill_name}` — `skill_view('{skill_name}')`.\n"

def main():
    args = parse_args()
    skill = args.skill
    display = args.name or skill
    
    profiles_dir = os.path.expanduser('~/.hermes/profiles')
    main_soul = os.path.expanduser('~/.hermes/SOUL.md')
    
    files = [main_soul] + [
        os.path.join(profiles_dir, d, 'SOUL.md')
        for d in sorted(os.listdir(profiles_dir))
        if os.path.isfile(os.path.join(profiles_dir, d, 'SOUL.md'))
    ]
    
    patched = 0
    skipped = 0
    for fpath in files:
        with open(fpath) as f:
            content = f.read()
        result = insert_skill_view(content, skill, display)
        if result:
            with open(fpath, 'w') as f:
                f.write(result)
            print(f"  PATCHED {os.path.relpath(fpath, os.path.expanduser('~/.hermes'))}")
            patched += 1
        else:
            skipped += 1
    
    print(f"\nDone: {patched} patched, {skipped} skipped (already had skill_view('{skill}'))")

if __name__ == '__main__':
    main()
