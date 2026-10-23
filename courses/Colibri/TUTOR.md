# Colibri

## Where things are

- The pitch deck: `docs/colibri-pitch/colibri-pitch.tex`, with its ink in `.ink/` and its feedback rounds on disk under `docs/colibri-pitch/feedback/` (untracked).
- The write-up behind it: `docs/writeup-20261012-111337/writeup.tex`, with the owner's pages in `handwritten/`.
- The sources: `materials/SOURCES.md` lists every file in `materials/`, its origin and the Atlas SHA it was copied at, plus the Colibri upstream and its two pins. `materials/` is Mac-only.

## Now

Lesson session 20261012-111337 resumes at card 0048. Its open question: the 576 numbers a block keeps per token (512 latent, 64 positional) are written when the token arrives. What are they computed from, and why does that count not depend on how many heads the block has?

The topic order, one concept per reply:

1. What Colibri is and where it runs.
2. Why it is safe with sensitive data: local weights, the fences, the egress block.
3. How it rides the cluster: Slurm, the relay, the 68-minute cold start.
4. The live gaps: loopback is not a boundary, ollama has no auth, KV persistence.
5. The partitions, the A40s and NVLink: why inactive NVLink favours replicas over shards.

The deck: round 2's 40 requests are unanswered, because the last revise timed out. The owner re-asks it from the library.

## Open decisions

## Done recently
