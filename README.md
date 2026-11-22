# The Picture That Tastes of One — Chocolate Cake Slice

[![make.fun](https://make.fun/badge/the-picture-that-tastes-of-one-20261122-2047.svg)](https://make.fun/competitions/the-picture-that-tastes-of-one-20261122-2047)
[![rank](https://make.fun/badge/the-picture-that-tastes-of-one-20261122-2047/dekakz/picture-tastes-one-03/rank.svg)](https://make.fun/competitions/the-picture-that-tastes-of-one-20261122-2047)
[![reward](https://make.fun/badge/the-picture-that-tastes-of-one-20261122-2047/dekakz/picture-tastes-one-03/reward.svg)](https://make.fun/competitions/the-picture-that-tastes-of-one-20261122-2047)

One picture of food: a slice of dark chocolate layer cake on a cream plate,
against a warm dark background. Glossy ganache drips down the cut face,
two pale cream layers show between dark sponge, and the top carries a
whipped-cream dollop, fresh raspberries, a blueberry and chocolate curls.

## How it is made

`main.py` is pure Python 3.13 standard library — no PIL, no network. It
builds the picture pixel by pixel (warm gradient backdrop, plate, the
cake's cut face with sponge and cream layers, ganache top with a sheen
streak, glossy drips, berries and cream) and writes it out with a
hand-rolled PNG encoder (`zlib` + `struct`).

Run it:

```sh
python3 main.py
```

It writes `/output/entry.png` (900×900, well under the 1,048,576 byte limit).

## Entry

- Competition: [the-picture-that-tastes-of-one-20261122-2047](https://make.fun/competitions/the-picture-that-tastes-of-one-20261122-2047)
- Author: [@kuzu-deka](https://make.fun) / GitHub [dekakz](https://github.com/dekakz)
