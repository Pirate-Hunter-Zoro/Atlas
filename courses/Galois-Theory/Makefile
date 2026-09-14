# ===========================================================================
#  Galois theory coursework — build entry points.
#
#  The ASSISTANT runs these, not the user (see AI_INSTRUCTIONS.md section 8).
#
#    make split            cut per-chapter excerpts out of the textbook
#    make scaffold         create chapter folders and .tex files (never clobbers)
#    make chapter CH=07    build chapter 7's notes and homework
#    make notes CH=07      build just the notes
#    make homework CH=07   build just the homework
#    make all              build every chapter that has .tex files
#    make clean            remove build directories
#    make board           bring up the live tutoring board
#    make list             show the chapter table
#
#  CH is also accepted by split and scaffold to limit them to one chapter.
# ===========================================================================
ROOT  := $(patsubst %/,%,$(dir $(abspath $(lastword $(MAKEFILE_LIST)))))
BUILD := bash "$(ROOT)/scripts/build.sh"

.PHONY: all split scaffold chapter notes homework clean list board board-stop board-export

split:
	@bash "$(ROOT)/scripts/split-textbook.sh" $(CH)

scaffold:
	@bash "$(ROOT)/scripts/scaffold.sh" $(CH)

chapter: notes homework

notes:
	@test -n "$(CH)" || { echo "usage: make notes CH=07"; exit 1; }
	@f=$$(ls "$(ROOT)"/chapters/ch$(CH)-*/notes/ch$(CH)-notes.tex 2>/dev/null | head -1); \
	 test -n "$$f" || { echo "no notes file for CH=$(CH) (try: make scaffold CH=$(CH))"; exit 1; }; \
	 $(BUILD) "$$f"

homework:
	@test -n "$(CH)" || { echo "usage: make homework CH=07"; exit 1; }
	@f=$$(ls "$(ROOT)"/chapters/ch$(CH)-*/homework/ch$(CH)-homework.tex 2>/dev/null | head -1); \
	 test -n "$$f" || { echo "no homework file for CH=$(CH) (try: make scaffold CH=$(CH))"; exit 1; }; \
	 $(BUILD) "$$f"

all:
	@fail=0; \
	 for f in "$(ROOT)"/chapters/ch*/notes/*.tex "$(ROOT)"/chapters/ch*/homework/*.tex; do \
	   [ -f "$$f" ] || continue; \
	   $(BUILD) "$$f" || fail=1; \
	 done; \
	 exit $$fail

clean:
	@rm -rf "$(ROOT)"/chapters/*/build
	@echo "build directories removed."

list:
	@grep -v '^#' "$(ROOT)/chapters.tsv" | awk -F'\t' 'NF{printf "ch%-3s pp.%-4s-%-4s %s\n",$$1,$$2,$$3,$$5}'

# --- live tutoring board (Tutor-Board) -------------------------------------
board:
	@board start

board-stop:
	@board stop

board-export:
	@board export --build
