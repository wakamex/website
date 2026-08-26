# From Quartz to Zola, bypassing Hugo

I just transferred [my knowledge base](https://ufopedia.fyi/) over to Zola. The starting point was Karpathy's [knowledge base post](https://x.com/karpathy/status/2039805659525644595) from April 2, 2026. Initially I built locally and viewed with [Obsidian](https://obsidian.md). Wanting a public view, I used [Quartz](https://quartz.jzhao.xyz/) which was very easy to set up. I started looking for alternatives when builds took over 4 minutes and 3 GB memory on 1000+ pages.

I chose Zola as a clean minimal alternative to Hugo. Zola and Hugo had equivalent build times in testing. Only Zola has native backlink tracking. And [PR#3116](https://github.com/getzola/zola/pull/3116) has wikilinks support. To extend Hugo, I considered writing a separate compatibility layer in Rust. Since Zola is written in Rust, I can extend it directly. Also the community feels like something I can contribute to, since the PR states they're looking for testers.

I started on the next branch, merged PR#3116, and added a few things along the way, all of which went quite smoothly. What worked well, what did I change, and what did I add?

### What went well
- All of my existing tags, and a few obvious improvements, fit well under the taxonomy system
- Customizing the theme to my liking was super easy
- Cloudflare deployment was a snap

### What I tweaked
- Disambiguation suggestions when a duplicate is found (I have 3)
- Let wikilinks point to aliases and allowlisted missing pages
- Allow markdown to render hard breaks, for single-line transcripts (optional)

### What I added
- Self-fragment links such as `[[#details]]`
- Ability to link to colocated assets and taxonomy terms
- Relative paths like `[[./sibling]]` and `[[../parent]]`
- Opt-in asset allowlisting and output-size limits

### Non-static stuff
I also moved away from Quartz's FlexSearch static search, to avoid a 6.3 MiB index (decoded to 18.21 MiB). I switched to D1 FTS5 search on the same Cloudflare worker that serves the site. It's about twice as accurate and fast. I got Zola to build the JSONL search corpus in a second pass over its already-rendered article HTML. This could probably be folded into the rendering pipeline as a single pass.
