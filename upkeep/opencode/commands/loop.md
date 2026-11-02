---
description: Run a prompt now and again on an interval, or self-paced (e.g. /loop 10m check the deploy)
---
Run this on a loop: $ARGUMENTS

1. If the text starts with an interval (30s, 5m, 2h, 1d), that is the period and the rest is the task. Otherwise the whole text is the task and you choose the period: short while things change fast, longer when nothing is happening.
2. Do the task once now.
3. Unless the task is finished or the user said to stop, call `wakeup` with the period in seconds. Its prompt must be the full loop instruction, starting with "/loop iteration:", carrying the task text, the period, and anything learned so far that the next round needs.
4. End your turn. Each `<wakeup>` message is the next iteration: do the task, then schedule the next one the same way.

Stop scheduling when the task is complete, when the user asks, or when continuing is pointless, and say why. A fixed-time schedule (every weekday at 9) belongs to `cron_create` instead.
