#!/usr/bin/env wolframscript
(* ------------------------------------------------------------------------
   strip-commentary.wls -- remove ANSWER COMMENTARY from an exercise notebook,
   keeping the problem statements and every line of code.

     wolframscript -file scripts/strip-commentary.wls report  NB [NB ...]
     wolframscript -file scripts/strip-commentary.wls apply   NB [NB ...]

   WHY. These notebooks arrived carrying prose that states what each piece of
   code returns and why it returns it. That analysis is the student's work to
   write, and AI_INSTRUCTIONS.md says so plainly: the assistant typesets THEIR
   mathematics, it does not write its own and put their name on it. The prose
   happens to be correct -- it was spot-checked against a live kernel -- but
   correctness was never the objection.

   THE RULE, and it is structural rather than a guess at meaning:

     within a section, a Text cell BEFORE any Input cell states the problem
                      a Text cell AFTER  an Input cell comments on the result

   The first is the professor's question restated and stays. The second is the
   answer and goes. Sections, Titles and every Input cell are untouched, so no
   code is lost and no question is lost.

   `report` changes nothing and prints the classification. Run it first.
   ------------------------------------------------------------------------ *)

args = Rest[$ScriptCommandLine];
mode = If[Length[args] > 0, First[args], "report"];
files = Rest[args];
If[! MemberQ[{"report", "apply"}, mode] || files === {},
  Print["usage: strip-commentary.wls report|apply NB [NB ...]"]; Exit[2]];

styleOf[Cell[_, s_String, ___]] := s;
styleOf[_] := "";
textOf[c_] := StringJoin[Cases[c, _String, Infinity]];

classify[cells_] := Module[{seenInput = False, out = {}},
  Do[
   Module[{st = styleOf[c]},
    Which[
     MemberQ[{"Section", "Subsection", "Subsubsection", "Title"}, st],
       seenInput = False; AppendTo[out, "keep"],
     MemberQ[{"Input", "Code", "Program"}, st],
       seenInput = True; AppendTo[out, "keep"],
     st === "Text",
       AppendTo[out, If[seenInput, "drop", "keep"]],
     True, AppendTo[out, "keep"]]],
   {c, cells}];
  out];

totKeep = 0; totDrop = 0;
Do[
 Module[{nb, cells, marks, dropped, kept},
  nb = Quiet@Check[Import[f], $Failed];
  If[Head[nb] =!= Notebook, Print["SKIP (not a notebook): ", f],
   cells = First[nb];
   marks = classify[cells];
   dropped = Pick[cells, marks, "drop"];
   kept = Pick[cells, marks, "keep"];
   totDrop += Length[dropped];
   totKeep += Count[marks, "keep"];
   Print["=== ", FileNameTake[f]];
   Print["    cells ", Length[cells], "  -> keep ", Length[kept],
         "  drop ", Length[dropped],
         "   (Input cells kept: ", Count[kept, c_ /; styleOf[c] === "Input"], ")"];
   If[mode === "report",
    Do[Print["      DROP: ",
       StringTake[StringReplace[textOf[d], {"\n" -> " ", "\r" -> " "}],
         UpTo[95]]], {d, Take[dropped, UpTo[3]]}];
    If[Length[dropped] > 3, Print["      ... and ", Length[dropped] - 3, " more"]],
    (* apply *)
    Export[f, ReplacePart[nb, 1 -> kept], "NB"];
    Print["    written"]]]],
 {f, files}];

Print[""];
Print["TOTAL kept ", totKeep, ", dropped ", totDrop, "  (mode: ", mode, ")"];
