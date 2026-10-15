# Third-party notices

## Ettin encoder and tokenizer

The model weights and tokenizer are derived from `jhu-clsp/ettin-encoder-17m`, revision `987607455c61e7a5bbc85f7758e0512ea6d0ae4c`. The upstream repository license is MIT: <https://raw.githubusercontent.com/jhu-clsp/ettin-encoder-vs-decoder/main/LICENSE>.

```text
MIT License

Copyright (c) 2025 Johns Hopkins University Center for Language and Speech Processing
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

The pinned Ettin source and revision, including its model card and repository, are documented at <https://huggingface.co/jhu-clsp/ettin-encoder-17m/tree/987607455c61e7a5bbc85f7758e0512ea6d0ae4c>.

## Training-source attribution

Training examples were adapted from the following sources; the original datasets are not redistributed in this package.

- **MBPP**, Google Research, pinned repository revision `f82046ba5aabbbb427dbfd38a254d26bff08b533`, Apache License 2.0. <https://github.com/google-research/google-research/tree/f82046ba5aabbbb427dbfd38a254d26bff08b533/mbpp>
- **GSM8K**, OpenAI, pinned revision `b0bb162abedc65e1fdd8e93ed090fd7598ee68bc`, MIT License. <https://github.com/openai/grade-school-math/tree/b0bb162abedc65e1fdd8e93ed090fd7598ee68bc>
- **SQL Create Context**, b-mc2, pinned revision `9d80a6a118b838d9defc3798d659a54a2ac2ff37`, CC BY 4.0. Its dataset card attributes underlying material to WikiSQL and Spider. <https://huggingface.co/datasets/b-mc2/sql-create-context/tree/9d80a6a118b838d9defc3798d659a54a2ac2ff37>
- Internally authored synthetic prompts were also used. They are not external source material.

Attribution, source revisions, checksums, and usage notes are recorded in the project's `reports/DATA_SOURCES.json` and `data/licenses/`. These references do not imply endorsement by the upstream authors.
