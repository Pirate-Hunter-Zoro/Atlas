# ===========================================================================
#  Mathematical modeling coursework — build entry points.
#
#  The ASSISTANT runs these, not the user (see AI_INSTRUCTIONS.md section 8).
#
#    make scaffold             create every unit's folders and .tex files
#    make scaffold-lessons     just the Mathematica lessons
#    make scaffold-chapters    just the Beltrami chapters
#    make lesson N=07          build lesson 7's notes
#    make notes CH=03          build Beltrami chapter 3's notes
#    make homework CH=03       build chapter 3's homework
#    make all                  build everything that has a .tex file
#    make clean                remove build directories
#    make board           bring up the live tutoring board
#    make list                 show the unit table
# ===========================================================================
ROOT  := $(patsubst %/,%,$(dir $(abspath $(lastword $(MAKEFILE_LIST)))))
BUILD := bash "$(ROOT)/scripts/build.sh"

.PHONY: all scaffold scaffold-lessons scaffold-chapters lesson notes homework clean list board board-stop board-export

scaffold:
	@bash "$(ROOT)/scripts/scaffold.sh"

scaffold-lessons:
	@bash "$(ROOT)/scripts/scaffold.sh" lesson $(N)

scaffold-chapters:
	@bash "$(ROOT)/scripts/scaffold.sh" chapter $(CH)

lesson:
	@test -n "$(N)" || { echo "usage: make lesson N=07"; exit 1; }
	@f=$$(ls "$(ROOT)"/lessons/lesson-$(N)/notes/*.tex 2>/dev/null | head -1); \
	 test -n "$$f" || { echo "no notes for lesson $(N) (try: make scaffold)"; exit 1; }; \
	 $(BUILD) "$$f"

notes:
	@test -n "$(CH)" || { echo "usage: make notes CH=03"; exit 1; }
	@f=$$(ls "$(ROOT)"/chapters/ch$(CH)-*/notes/ch$(CH)-notes.tex 2>/dev/null | head -1); \
	 test -n "$$f" || { echo "no notes for chapter $(CH) (try: make scaffold)"; exit 1; }; \
	 $(BUILD) "$$f"

homework:
	@test -n "$(CH)" || { echo "usage: make homework CH=03"; exit 1; }
	@f=$$(ls "$(ROOT)"/chapters/ch$(CH)-*/homework/ch$(CH)-homework.tex 2>/dev/null | head -1); \
	 test -n "$$f" || { echo "no homework for chapter $(CH) (try: make scaffold)"; exit 1; }; \
	 $(BUILD) "$$f"

all:
	@fail=0; \
	 for f in "$(ROOT)"/lessons/*/notes/*.tex "$(ROOT)"/chapters/ch*/notes/*.tex "$(ROOT)"/chapters/ch*/homework/*.tex; do \
	   [ -f "$$f" ] || continue; \
	   $(BUILD) "$$f" || fail=1; \
	 done; \
	 exit $$fail

clean:
	@rm -rf "$(ROOT)"/lessons/*/build "$(ROOT)"/chapters/*/build
	@echo "build directories removed."

list:
	@grep -v '^#' "$(ROOT)/units.tsv" | awk -F'\t' 'NF{printf "%-8s %-3s %s\n",$$1,$$2,$$4}'

# --- live tutoring board (Tutor-Board) -------------------------------------
board:
	@board start

board-stop:
	@board stop

board-export:
	@board export --build
