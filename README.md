# htmldiff

Given two text files, this script generates an HTML page modeled after VS Code's diff viewer. It supports side-by-side or one-column layout, word-level highlighting, wrapped paragraphs that stay aligned, Prev/Next navigation, and the ability to collapse unchanged sections.

This script embeds both texts in the output page, with the diff getting computed by the browser at runtime.

## Usage

```sh
python htmldiff.py ORIGINAL REVISED [-o OUT.html] [-t TITLE] \
    [--left-label TEXT] [--right-label TEXT] [--open]
```

Output is written to `ORIGINAL-vs-REVISED.html` in the current folder by default. Add `--open` to view it in a browser right away.

To change the page's look or behavior, edit `TEMPLATE` at the bottom of `htmldiff.py`.
