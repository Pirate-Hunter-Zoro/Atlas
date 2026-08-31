#!/usr/bin/env wolframscript
(* ------------------------------------------------------------------------
   rebuild-exercises.wls -- rebuild a lesson's exercise notebook around the
   PROFESSOR'S OWN question cells, with the student's code under each one.

     wolframscript -file scripts/rebuild-exercises.wls report [NN ...]
     wolframscript -file scripts/rebuild-exercises.wls apply  [NN ...]
     wolframscript -file scripts/rebuild-exercises.wls apply all COMMENTARY.tsv

   WHY. The submitted PDFs used to carry section headings the assistant had
   WRITTEN -- "2: The numerical function N", "5: Symbols as units" -- with the
   code underneath and the actual question nowhere on the page. A grader could
   not tell what was being answered, and the headings were an invention sitting
   under the student's name. Both are the same failure the README records for
   30 August 2026, in a smaller coat.

   THE RULE. Everything the reader sees that is not code comes out of
   "Adv Lesson NN.nb" byte for byte:

     - the Exercises section header, and the professor's Your Name / Your Math
       Class cell with the name filled in;
     - his preamble cells ("Note: ... convert every day notation ...",
       "Remember to clear all variables ...");
     - every numbered question cell, in his order, with his numbering -- which
       in Lesson 11 means two exercises numbered 14, kept as two 14s;
     - any cell he wrote inside a question (Lesson 4's someData = Table[...]
       input, his two expected-output figures).

     and the student's Input cells are inserted after the last cell of the
     question they answer. Nothing else is added. Text cells in work/ are
     assistant commentary and are dropped -- see lessons/ASSISTANT-NOTES.md,
     which is where the ones worth keeping were written down.

   THE PAIRING is by ORDER, not by number: the k-th question cell in the
   professor's notebook takes the code under the k-th Section in work/. That is
   the only rule that survives Lesson 11's repeated 14. The script refuses to
   write anything unless the two counts agree, so a notebook that has already
   been rebuilt (its Sections are now the professor's, and there are one or
   three of them, not eighteen) is skipped rather than mangled.

   Everything the professor wrote after the last question -- "Print your
   homework exercises ...", the printing screenshots -- is cut. It is
   instructions for producing the submission, not part of it.

   `report` writes nothing and prints the question-to-section pairing. Run it
   first, and read it: a wrong pairing is silent, a mismatched count is not.
   The optional third argument to `apply` is a TSV file the dropped commentary
   is written to.
   ------------------------------------------------------------------------ *)

args = Rest[$ScriptCommandLine];
mode = If[Length[args] > 0, First[args], "report"];
If[! MemberQ[{"report", "apply"}, mode],
  Print["usage: rebuild-exercises.wls report|apply [NN ...|all] [COMMENTARY.tsv]"]; Exit[2]];

root = ParentDirectory[DirectoryName[$InputFileName]];
rest = Rest[args];
notesOut = SelectFirst[rest, StringEndsQ[#, ".tsv"] &, None];
nums = Select[rest, StringMatchQ[#, DigitCharacter ..] &];
If[nums === {} || MemberQ[rest, "all"], nums = IntegerString[Range[1, 16], 10, 2]];

student = "Mikey Ferguson";
mathClass = "MATH 7013 - Advanced Mathematical Modeling";

styleOf[Cell[_, s_String, ___]] := s;
styleOf[_] := "?";
textOf[c_] := StringJoin[Cases[c, _String, Infinity]];
oneLine[t_] := StringReplace[t, {"\n" -> " ", "\t" -> " ", "\r" -> " "}];
flat[cells_] := Flatten[cells //. {CellGroupData[cs_, ___] :> cs,
                                   Cell[CellGroupData[cs_, ___]] :> cs}];

(* a question cell opens with its number: "3:", "10:", "16." -- and the styled
   runs inside it join as "10Bold:", hence the letters in the middle. *)
questionQ[c_] := styleOf[c] === "Text" &&
  StringMatchQ[oneLine[textOf[c]], RegularExpression["^[ ]*[0-9]+[A-Za-z ]*[:.].*"]];

codeQ[c_] := MemberQ[{"Input", "InputOnly", "Code", "Program"}, styleOf[c]];

fillName[c_] := c /. s_String :> StringReplace[s, {
   "Your Name:" -> "Your Name:  " <> student,
   "Your Math Class:" -> "Your Math Class:  " <> mathClass}];

notes = If[mode === "apply" && notesOut =!= None, OpenWrite[notesOut], None];
fail = 0;

Do[
 Module[{mf, wf, mc, wnb, wc, opts, exIdx, ex, cutPos, qpos, wsec, preCode,
         answers, dropped, res, blockEnd},
  mf = FileNameJoin[{root, "lessons", "lesson-" <> nn, "material", "Adv Lesson " <> nn <> ".nb"}];
  wf = FileNameJoin[{root, "lessons", "lesson-" <> nn, "work", "Adv Lesson " <> nn <> " Exercises.nb"}];
  If[! FileExistsQ[mf] || ! FileExistsQ[wf],
   Print["lesson ", nn, ": no material or no exercise notebook -- skipped"],

   mc = flat[First[Import[mf]]];
   wnb = Import[wf];
   wc = flat[First[wnb]];
   opts = Rest[List @@ wnb];

   (* the exercise set is the last Section whose title says "Exercise" *)
   exIdx = Last[Flatten[Position[mc, c_ /; styleOf[c] === "Section" &&
       StringContainsQ[textOf[c], "Exercise"], {1}]]];
   ex = Drop[mc, exIdx - 1];
   cutPos = SelectFirst[Range[2, Length[ex]],
      StringContainsQ[oneLine[textOf[ex[[#]]]], "homework exercises", IgnoreCase -> True] &,
      Length[ex] + 1];
   ex = Take[ex, cutPos - 1];
   While[Length[ex] > 0 && (styleOf[Last[ex]] === "Program" ||
         StringTrim[textOf[Last[ex]]] === ""), ex = Most[ex]];
   ex = MapIndexed[If[First[#2] == 2 && styleOf[#1] === "Program", fillName[#1], #1] &, ex];
   qpos = Flatten[Position[ex, c_ /; questionQ[c], {1}]];

   wsec = Flatten[Position[wc, c_ /; styleOf[c] === "Section", {1}]];
   (* code written before the first section answers "Remember to clear ..." *)
   preCode = If[wsec === {}, {}, Select[Take[wc, First[wsec] - 1], codeQ]];
   answers = Table[
     Module[{a = wsec[[i]] + 1, b = If[i < Length[wsec], wsec[[i + 1]] - 1, Length[wc]]},
       Select[Take[wc, {a, b}], codeQ]], {i, Length[wsec]}];

   Print["=== lesson ", nn, ": ", Length[qpos], " questions, ", Length[wsec],
     " sections in work/", If[Length[qpos] === Length[wsec], "", "   <<< MISMATCH, refusing"]];
   Do[Print["   Q", i, "  ", StringTake[oneLine[textOf[ex[[qpos[[i]]]]]], UpTo[64]],
       "  <=  ", If[i <= Length[wsec], StringTake[oneLine[textOf[wc[[wsec[[i]]]]]], UpTo[48]], "NOTHING"],
       "  [", If[i <= Length[answers], Length[answers[[i]]], 0], " code]"],
    {i, Length[qpos]}];

   If[Length[qpos] =!= Length[wsec], fail = 1,

    If[notes =!= None,
     Do[Module[{a = wsec[[i]] + 1, b = If[i < Length[wsec], wsec[[i + 1]] - 1, Length[wc]]},
        Do[WriteString[notes, nn, "\t", oneLine[textOf[wc[[wsec[[i]]]]]], "\t",
             ToString[oneLine[textOf[t]], InputForm], "\n"],
         {t, Select[Take[wc, {a, b}], styleOf[#] === "Text" &]}]],
      {i, Length[wsec]}];
     If[wsec =!= {} && First[wsec] > 1,
      Do[WriteString[notes, nn, "\t(before the first section)\t",
           ToString[oneLine[textOf[t]], InputForm], "\n"],
       {t, Select[Take[wc, First[wsec] - 1], styleOf[#] === "Text" &]}]]];

    If[mode === "apply",
     res = {};
     Do[
      If[qpos =!= {} && i === First[qpos] && preCode =!= {}, res = Join[res, preCode]];
      AppendTo[res, ex[[i]]];
      blockEnd = SelectFirst[Range[Length[qpos]],
         (qpos[[#]] <= i && (# === Length[qpos] || qpos[[# + 1]] > i)) &, 0];
      If[blockEnd > 0 && (blockEnd === Length[qpos] && i === Length[ex] ||
          blockEnd < Length[qpos] && i === qpos[[blockEnd + 1]] - 1),
        res = Join[res, answers[[blockEnd]]]],
      {i, Length[ex]}];
     Export[wf, Notebook[res, Sequence @@ opts], "NB"];
     Print["   written: ", Length[res], " cells (",
       Count[res, c_ /; codeQ[c]], " code)"]]]]],
 {nn, nums}];

If[notes =!= None, Close[notes]];
Exit[fail]
