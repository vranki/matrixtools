# MatrixTools

Simple tools to do stuff with Matrix.

## Mxtool

A command line python tool that currently can:

* Plumb IRC channels to existing Matrix rooms
* Leave rooms (faster than using Riot ui)
* Op / Deop IRC users

Currently only IRCNet is supported - support for other networks
coming later.


```bash
pipenv shell
pipenv install
python3 mxtool.py

(or to use access token):

MATRIX_USER="@user:matrix.org" MATRIX_ACCESS_TOKEN="longaccesstoken" MATRIX_SERVER="https://matrix.org" python3 mxtool.py
```

Settings are stored to matrixtool.conf, delete it to reset.
