# Go Algorithms

## Where things are

`RULES.md` is the coaching contract. `QUESTS.md` holds the topics. `go.mod` exists: module `github.com/Pirate-Hunter-Zoro/Atlas/projects/Go-Algorithms`, `go 1.27.4`. The dynamic array lives at `ds/dynamicarray/dynamicarray.go`, package `dynamicarray`, and is `gofmt`-clean. `gofmt -l`, `go build ./...` and `go vet ./...` all come back clean. There is no test file in `ds/dynamicarray` yet, so no bench, `scripts/check.sh` or `tutorboard.json` check exists.

## Now

Dynamic array, generic. `Cap` and `Append` are correct. The append trace on the actual file gives Len/Cap/values 1/2/[1] through 7/14/[1..7]; every value survives. `gofmt -w` has been run: `gofmt -l` silent, `go build ./...` and `go vet ./...` exit 0.

The amortized cost claim is argued and agreed. Accounting at 3 units per element gives $O(3n)=O(n)$; the true copy total is $n-1$, so total work stays under $2n$. Written up as the `append-cost` problem.

Standing instruction from the owner, 2026-11-19: no prediction questions, ever. He is not asked to guess a ratio, a bound, an exponent or an outcome before a measurement. State the expectation, then measure. He wants proofs and coding. This holds until he reopens it. The "the owner predicts it first" clause in RULES.md is his to strike; the tutor never edits that file.

Remaining work is the measurement: a doubling benchmark at 1000, 2000, 4000, 8000 in `ds/dynamicarray`, one `BenchmarkAppend` using `b.Run` and `b.Loop`, written by the owner. The coach runs `go test -bench` and reports the table. Card 0014 poses exactly that; nothing else is on the route.

## Open decisions

- Constraint: the dynamic array uses `T any`, because nothing compares. The `cmp.Ordered` versus comparison-function choice stays open for ordered structures later.
- Topic after graphs: the owner's choice.

## Done recently
