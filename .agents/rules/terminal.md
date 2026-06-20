---
trigger: always_on
---

You should avoid using the terminal to read or search for files, such as with cat or grep. Additionally, do not use git in the terminal. If you must use the terminal for something python related, use uv. For example, do not try to do "python ..." because this will always break as it does not use the installed venv, you MUST use "uv run". Do not attempt to mess with the packages or venvs. Furthermore, do not attempt to run any project scripts that are not testing scripts you made, especially those that will take a while.