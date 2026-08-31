#!/usr/bin/env wolframscript
(* ------------------------------------------------------------------------
   nb2pdf.wls -- print notebooks to PDF the way Mathematica prints them.

     wolframscript -file scripts/nb2pdf.wls IN1.nb OUT1.pdf IN2.nb OUT2.pdf ...

   Arguments come in in/out PAIRS, and many pairs are handled in ONE run on
   purpose: the kernel takes the better part of a minute to start, so sixteen
   separate invocations cost sixteen startups and one costs one.

   WHY THIS AND NOT scripts/nb2tex.py. This is the real thing -- the notebook's
   own styles, and its two-dimensional typeset input drawn as a built-up
   fraction rather than respelled as a/b. It is what "a printed notebook" means.
   It needs an ACTIVATED Wolfram Engine, which is per-machine and interactive
   (see WOLFRAM-LICENSE.md); nb2tex.py needs no kernel at all and is the
   fallback on a machine where that has not happened yet.

   OUTPUT CELLS ARE DROPPED HERE TOO. The submission format for this course is a
   printed notebook with the output cleared. The exercise notebooks currently
   hold none, so today this changes nothing -- but the moment one is evaluated
   it would, and a submission that silently starts carrying output is the
   failure worth spending five lines to prevent.
   ------------------------------------------------------------------------ *)

args = Rest[$ScriptCommandLine];

If[Length[args] < 2 || OddQ[Length[args]],
  Print["usage: nb2pdf.wls IN.nb OUT.pdf [IN.nb OUT.pdf ...]"];
  Exit[2]];

(* Cell styles that are machine output rather than authored content. *)
outputStyles = {"Output", "Print", "Message", "Echo"};

stripOutput[nb_Notebook] := Module[{cells = First[nb], kept},
  kept = DeleteCases[cells,
    Cell[_, s_String /; MemberQ[outputStyles, s], ___], Infinity];
  ReplacePart[nb, 1 -> kept]];

fail = 0;
Do[
  Module[{in = args[[2 i - 1]], out = args[[2 i]], nb, dropped, res},
    If[! FileExistsQ[in],
      Print["MISSING: ", in]; fail = 1,
      nb = Quiet@Check[Import[in], $Failed];
      If[Head[nb] =!= Notebook,
        Print["NOT A NOTEBOOK: ", in]; fail = 1,
        dropped = Count[First[nb],
          Cell[_, s_String /; MemberQ[outputStyles, s], ___], Infinity];
        nb = stripOutput[nb];
        res = Quiet@Check[Export[out, nb], $Failed];
        If[res === $Failed || ! FileExistsQ[out],
          Print["FAILED: ", in]; fail = 1,
          Print["OK: ", out,
            " (", Import[out, "PageCount"], " pages",
            If[dropped > 0, ", " <> ToString[dropped] <> " output cell(s) dropped", ""],
            ")"]]]]],
  {i, Length[args]/2}];

Exit[fail]
