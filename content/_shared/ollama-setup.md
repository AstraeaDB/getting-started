Making an embedding needs a model, and running one locally is easier than it
sounds. [Ollama](https://ollama.com) is a small program that downloads a model
and serves it over a web address on your own machine, so nothing you write here
leaves your computer. Install it from their site, then pull the model this site
uses:

<!-- verify: skip reason="the verification images talk to an Ollama already running on the host, so pulling a model inside the container would download several hundred megabytes on every run" -->
```bash
ollama pull embeddinggemma
```

That model is called `embeddinggemma`, and it turns a piece of text into a list
of 768 numbers. Once it has finished downloading, check that Ollama is
answering:

<!-- verify: skip reason="the verification images talk to an Ollama already running on the host, so this would report the host's models rather than the container's" -->
```bash
curl http://localhost:11434/api/tags
```

You should see a block of text listing the models you have pulled, with
`embeddinggemma` among them. Leave Ollama running while you work through this
lesson.
