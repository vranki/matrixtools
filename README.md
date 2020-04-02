# MatrixTools

Simple tools to do stuff with Matrix. WIP.

## Mxtool

A command line python tool that currently can:

* Plumb IRCNet rooms
* Leave rooms (faster than using Riot ui)

```bash
pipenv shell
pipenv install
MATRIX_USER="@user:matrix.org" MATRIX_ACCESS_TOKEN="longaccesstoken" MATRIX_SERVER="https://matrix.org" python3 mxtool.py
```
