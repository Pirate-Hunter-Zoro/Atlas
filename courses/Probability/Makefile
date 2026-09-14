# ===========================================================================
#  Probability coursework — build entry points.
#
#  The ASSISTANT runs these, not the user (see AI_INSTRUCTIONS.md section 8).
#
#    make split            cut per-chapter excerpts out of the textbook
#    make scaffold         create chapter folders and notes .tex (never clobbers)
#    make scaffold-hw HW=4 create homework set 04's folder and .tex
#    make notes CH=03      build chapter 3's notes
#    make homework HW=02   build homework set 2
#    make all              build everything that has a .tex file
#    make clean            remove build directories
#    make board           bring up the live tutoring board
#    make list             show the chapter table
# ===========================================================================
ROOT  := $(patsubst %/,%,$(dir $(abspath $(lastword $(MAKEFILE_LIST)))))
BUILD := bash "$(ROOT)/scripts/build.sh"

.PHONY: all split scaffold scaffold-hw notes homework clean list board board-stop board-export

split:
	@bash "$(ROOT)/scripts/split-textbook.sh" $(CH)

scaffold:
	@bash "$(ROOT)/scripts/scaffold.sh" $(CH)

scaffold-hw:
	@test -n "$(HW)" || { echo "usage: make scaffold-hw HW=04"; exit 1; }
	@bash "$(ROOT)/scripts/scaffold.sh" --hw $(HW)

notes:
	@test -n "$(CH)" || { echo "usage: make notes CH=03"; exit 1; }
	@f=$$(ls "$(ROOT)"/chapters/ch$(CH)-*/notes/ch$(CH)-notes.tex 2>/dev/null | head -1); \
	 test -n "$$f" || { echo "no notes file for CH=$(CH) (try: make scaffold CH=$(CH))"; exit 1; }; \
	 $(BUILD) "$$f"

homework:
	@test -n "$(HW)" || { echo "usage: make homework HW=02"; exit 1; }
	@f=$$(ls "$(ROOT)"/homework/hw$(HW)/hw$(HW).tex 2>/dev/null | head -1); \
	 test -n "$$f" || { echo "no homework file for HW=$(HW) (try: make scaffold-hw HW=$(HW))"; exit 1; }; \
	 $(BUILD) "$$f"

all:
	@fail=0; \
	 for f in "$(ROOT)"/chapters/ch*/notes/*.tex "$(ROOT)"/homework/hw*/*.tex; do \
	   [ -f "$$f" ] || continue; \
	   $(BUILD) "$$f" || fail=1; \
	 done; \
	 exit $$fail

clean:
	@rm -rf "$(ROOT)"/chapters/*/build "$(ROOT)"/homework/*/build
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
