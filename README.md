# ![icon](src/himena/resources/icon-36x36.png) Himena

[![PyPI - Version](https://img.shields.io/pypi/v/himena.svg)](https://pypi.org/project/himena)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/himena.svg)](https://pypi.org/project/himena)
[![Python package index download statistics](https://img.shields.io/pypi/dm/himena.svg)](https://pypistats.org/packages/himena)
[![codecov](https://codecov.io/gh/hanjinliu/himena/graph/badge.svg?token=7BS2gF92SL)](https://codecov.io/gh/hanjinliu/himena)

-----

![](images/window.png)

`himena` is an infinitely extensible and reusable applications framework for data
science.

<details><summary><b>Motivation</b></summary>

There are many GUI applications for data science, and many of them use the "plugin
system" to extend their functionality. Even though the plugin system is a good idea,
there are plenty of duplicated works in the third-party plugins.

The reason is that **plugins cannot extend other plugins**. Imagine that you are a
plugin developer and making a plugin that extract features from images as a table. To
make your plugin more useful, you will need to implement not only the table widget, but
filter/sort functions, plotting functions, and I/O functions as well. You will also be
sad to find that these functions cannot readily be used in other plugins.

`himena` is designed so that **plugins developers can cooperate with each other**. The
table widgets you implemented in your plugin can be used by other plugins that return a
tabular data. The plotting functions you implemented in your plugin can be used from
any table widgets implemented in other plugins.

To join this plugin community, please check out the [developer's guide](https://hanjinliu.github.io/himena/dev/).

</details>

### Documentation

Tutorial, developer's guide, and API reference are available at the [documentation site](https://hanjinliu.github.io/himena/).

## Installation

`himena` is available on PyPI.

```shell
pip install himena -U
```

Alternatively, you can install the latest version from GitHub.

```shell
git clone git+https://github.com/hanjinliu/himena
cd himena
pip install -e .
```

## Start application

```shell
himena
```

## Existing Plugins

You can customize `himena` for your needs by installing plugins. Here's some example plugins:

- [himena-image](https://github.com/hanjinliu/himena-image): image processing and analysis
- [himena-stats](https://github.com/hanjinliu/himena-stats): statistical testing and modeling.
- [himena-seaborn](https://github.com/hanjinliu/himena-seaborn): [seaborn](https://github.com/mwaskom/seaborn) plotting.
- [himena-lmfit](https://github.com/hanjinliu/himena-lmfit): Curve fitting and parameter optimization using [lmfit](https://lmfit.github.io/lmfit-py/model.html).
- [himena-bio](https://github.com/hanjinliu/himena-bio): widgets and commands for basic bioinformatics analysis using [biopython](https://github.com/biopython/biopython).
- [himena-relion](https://github.com/hanjinliu/himena-relion): A modern RELION GUI built on `himena`.
- [napari-himena](https://github.com/hanjinliu/napari-himena): Sending data between `napari` and `himena`.
