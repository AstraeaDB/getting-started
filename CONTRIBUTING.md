# Contributing

This site is built from Markdown in `content/`, rendered by `site/build.py`,
and checked by running every code block inside a container. Prose and code are
held to the same standard: if the page claims something, something proves it.

## The five style rules

Every piece of prose on this site follows these. They are not preferences.

1. **Avoid em-dashes.** Do not use `—`. Use a comma, a colon, a semicolon,
   parentheses, or split the sentence in two. Do not substitute an en-dash or a
   double hyphen; restructure instead. Em-dashes are fine inside code blocks,
   where they are part of an example the reader runs.
2. **No sentence fragments.** Every sentence has a subject and a verb. Rewrite
   stray noun phrases and heading-like lines into full sentences.
3. **Approachable but not overly familiar.** Warm, plain, and professional,
   like a patient instructor. Address the reader as "you". Avoid hype and
   slang: no "let's build something", no "earns its keep", no "see you there".
4. **Avoid jargon.** Prefer plain language. When a technical term is genuinely
   needed, define it in ordinary words the first time it appears, and spell out
   acronyms on first use (GQL, WASM, LLM, HNSW).
5. **Explain difficult concepts clearly for beginners.** Before showing how to
   do something, make sure a newcomer understands what it is and why it
   matters. Short, concrete analogies are welcome.

## Structure

- One H1 title, then one italic subtitle sentence, then a two or three sentence
  hook, then `##` sections.
- The first line is an HTML comment holding an SEO meta description of about
  150 to 160 characters, free of em-dashes.
- Fence every code block with a language tag, so the verifier knows whether to
  run it: ```` ```python ````, ```` ```r ````, ```` ```bash ````, ```` ```rust ````.
- Roughly 1,100 to 1,600 words of prose. Clear beginner explanations may push a
  little higher.
- Link sibling lessons with relative Markdown links, `[Title](./file.md)`. The
  build rewrites `.md` to `.html`.

## Accuracy is the point

This is the rule that makes the rest worth reading.

- **Use only real APIs.** Every method and every request type must exist. If
  you are unsure, run it.
- **Verify every claimed output against a live server.** Not against your
  memory of one. Numbers in prose (distances, scores, counts, accuracies) are
  wrong surprisingly often, and readers notice.
- **A check that cannot fail is not a check.** Before trusting a test, break
  the thing it watches and confirm it goes red. Several bugs have shipped here
  behind checks that passed while doing nothing.
- **Presence is not function.** Finding a symbol in a source tree proves the
  code exists, not that it works. Four dashboard features once passed review
  that way and did nothing at all when clicked.

## Verification

Every lesson declares `verify = "required" | "manual" | "none"` in
`lessons.toml`, and `/status.html` publishes the result. A lesson is green only
when every code block runs in a fresh container against a real AstraeaDB, exits
zero, matches its expected output after normalization, and writes nothing to
stderr.

```bash
just build                    # render content/ into docs/
just verify crawl-py-01       # run one lesson's blocks in a container
just verify-all               # every lesson marked required
just self-test                # prove the harness itself still works
```

Skipping a block requires a reason:

```markdown
<!-- verify: skip reason="pulls a multi-gigabyte model" -->
```

The reason is published on the status page. Silent skips are refused by the
extractor, because a suite that quietly stops checking things is worse than no
suite.

Steps that need a human, such as anything driving a browser, live in
`verify/manual/` as a checklist with dated results. Tick a box only after
watching the behaviour, and record what you observed rather than that you
looked.

## Sample projects are generated

`samples/<lesson-id>/` is produced from the lesson's own code blocks by
`site/sync_samples.py`, and `just build` fails if the two drift. Edit the
lesson, then run `just sync-samples`. Never edit a generated file directly.

## Before opening a pull request

```bash
just sync-samples
just build            # fails on stale samples and unresolvable links
just verify <lesson>  # for any lesson whose code you touched
```

Then read your prose once more against the five rules. The em-dash rule catches
more real problems than it looks like it should, because the sentences that
want an em-dash are usually the ones carrying two ideas that deserve to be
separated.
