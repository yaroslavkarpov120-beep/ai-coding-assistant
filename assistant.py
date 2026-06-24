#!/usr/bin/env python3
"""AI Coding Assistant — powered by OpenRouter"""

import os
import sys
import subprocess
from pathlib import Path

try:
    from openai import OpenAI
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.prompt import Prompt
    from rich import print as rprint
    import git
except ImportError:
    print("Run: source venv/bin/activate")
    sys.exit(1)

console = Console()
API_KEY_FILE = Path.home() / ".ai_assistant_key"

def get_api_key():
    if API_KEY_FILE.exists():
        return API_KEY_FILE.read_text().strip()
    key = input("Вставь OpenRouter API ключ: ").strip()
    API_KEY_FILE.write_text(key)
    return key

def get_codebase_context(path="."):
    files = []
    extensions = {'.py','.js','.ts','.jsx','.tsx','.html','.css','.go','.rs','.java','.cpp','.c','.rb'}
    try:
        for f in Path(path).rglob("*"):
            if f.is_file() and f.suffix in extensions and ".git" not in str(f) and "venv" not in str(f):
                files.append(str(f.relative_to(path)))
    except Exception:
        pass
    return files

def run_command(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return "Команда превысила лимит времени (30с)"
    except Exception as e:
        return f"Ошибка: {e}"

def git_commit(message, path="."):
    try:
        repo = git.Repo(path)
        repo.git.add(A=True)
        repo.index.commit(message)
        return f"✓ Закоммичено: {message}"
    except git.InvalidGitRepositoryError:
        return "Это не git репозиторий"
    except Exception as e:
        return f"Ошибка git: {e}"

def build_system_prompt(codebase_files):
    files_str = "\n".join(codebase_files[:50]) if codebase_files else "Нет файлов"
    return f"""Ты — AI Coding Assistant. Отвечай на русском языке.

Структура текущего проекта:
{files_str}

Ты умеешь писать код, находить баги, объяснять решения.
Когда предлагаешь код — указывай имя файла.
Отвечай конкретно и по делу."""

HELP = """
[bold cyan]Команды:[/bold cyan]
  [green]run <команда>[/green]       — выполнить команду в терминале
  [green]commit <сообщение>[/green]  — закоммитить в git
  [green]scan[/green]                — показать файлы проекта
  [green]clear[/green]               — очистить историю чата
  [green]exit[/green]                — выйти
  Или просто пиши вопрос по коду!
"""

def main():
    console.print(Panel.fit(
        "[bold white]AI Coding Assistant[/bold white]\n[dim]Powered by OpenRouter[/dim]",
        border_style="cyan"
    ))

    api_key = get_api_key()
    client = OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1"
    )

    codebase = get_codebase_context(".")
    history = []
    system_prompt = build_system_prompt(codebase)

    console.print(f"[dim]Файлов в проекте: {len(codebase)}[/dim]")
    console.print("[dim]Напиши [bold]help[/bold] для списка команд[/dim]\n")

    while True:
        try:
            user_input = input("> ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Пока![/dim]")
            break

        if not user_input:
            continue

        if user_input.lower() == "exit":
            console.print("[dim]Пока![/dim]")
            break
        elif user_input.lower() == "help":
            console.print(HELP)
            continue
        elif user_input.lower() == "clear":
            history = []
            console.print("[green]История очищена[/green]")
            continue
        elif user_input.lower() == "scan":
            files = get_codebase_context(".")
            console.print(Panel("\n".join(files) if files else "Нет файлов", title="Файлы проекта", border_style="dim"))
            continue
        elif user_input.lower().startswith("run "):
            output = run_command(user_input[4:])
            console.print(Panel(output or "(нет вывода)", title="Результат", border_style="dim"))
            continue
        elif user_input.lower().startswith("commit "):
            console.print(f"[green]{git_commit(user_input[7:])}[/green]")
            continue

        history.append({"role": "user", "content": user_input})

        MODELS = [
            "openai/gpt-oss-20b:free",
            "google/gemma-4-31b-it:free",
            "meta-llama/llama-3.3-70b-instruct:free",
            "qwen/qwen3-coder:free",
        ]
        try:
            reply = None
            with console.status("[dim]Думаю...[/dim]"):
                for model in MODELS:
                    try:
                        response = client.chat.completions.create(
                            model=model,
                            messages=[{"role": "system", "content": system_prompt}] + history,
                        )
                        reply = response.choices[0].message.content
                        break
                    except Exception:
                        continue
            if reply is None:
                raise Exception("Все модели недоступны, попробуй через минуту")

            history.append({"role": "assistant", "content": reply})
            console.print()
            console.print(Markdown(reply))
            console.print()

        except Exception as e:
            console.print(f"[red]Ошибка: {e}[/red]")
            history.pop()

if __name__ == "__main__":
    main()
