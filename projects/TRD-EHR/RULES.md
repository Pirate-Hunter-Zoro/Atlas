# TRD-EHR rules

## Patient data

- Patient data never leaves the cluster. Never read anything under results/ or phi/. What reaches the Mac is exports/, and an export is the owner's call: they mark it aggregate.
- The check and every report carry only aggregate RELAY: lines.
- Long work goes to the cluster through `board job`, never a bare sbatch.

## The papers

- Two names for the two representations: the feature representation and the embedded representation. "Rule-based" is banned; a third name reads as a third method.
- The study population is a 4:1 case-enriched extract by design. Say so in Methods prose, never as a limitation. 501,718 is the delivered extract, never a source population. Never cite the SFHS query document.
- Methods does not grow. New material goes in its Supplement M-section; anything removed from the packet gets an entry in reserve/methods_reserve.md.
- No farthest-neighbour retrieval in any document.
- Panels are wide and short at the full 6in width. A page gap is fixed at the source, through PANEL_FIGSIZE in scripts/shared/plots.py, never by a narrower width in the Markdown.
- Where a task sets one step per turn (the clarity pass), finish one, hand it over and wait.

## The work

- The owner writes the statistics: every task marked Coach is theirs to write while you guide.
- A blocked task is the answer. Say what it waits on and stop; do not find filler work.
