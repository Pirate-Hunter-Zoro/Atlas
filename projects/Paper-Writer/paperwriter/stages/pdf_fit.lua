-- pdf_fit.lua -- keep a PDF's tables, code and paths inside the page.
--
-- Pandoc's LaTeX writer leaves three things at their natural width, and on a
-- page that is narrower than them they run off the right edge with no error:
--
--   * a SIMPLE table gets no column widths, so each column is as wide as its
--     longest cell and a six-column results table is wider than the page;
--   * a code block is `verbatim`, which never breaks a line, and a patient
--     narrative is one long line per field;
--   * inline code is `\texttt`, which never hyphenates, so a long file path
--     sticks out of a justified paragraph.
--
-- Only the PDF changes. A .docx lays its own tables out and wraps its own code,
-- and the journal copy must not be touched by a fix for the reading copy.

if not FORMAT:match("latex") then
  return {}
end

-- About as many characters of DejaVu Sans as a line of the default page holds.
-- A table whose cells fit in this is left at its natural widths.
local LINE_CHARS = 62
-- The same line at the two sizes a widened table is set in.
local SMALL_CHARS = 68
local FOOTNOTE_CHARS = 76
-- Each column keeps room for its longest word plus this much padding, because
-- a word is never broken and one wider than its column prints over the next.
-- Three, not two: a heading is bold, and bold DejaVu is wider.
local WORD_PAD = 3
-- Inline code shorter than this fits on any line and is left to pandoc.
local LONG_CODE = 24

local function longest_word(text)
  local most = 0
  for word in text:gmatch("%S+") do
    local len = utf8.len(word) or #word
    if len > most then most = len end
  end
  return most
end

-- Per column: the longest cell and the longest single word, in characters.
local function widest(tbl)
  local n = #tbl.colspecs
  local w, words = {}, {}
  for i = 1, n do w[i] = 0; words[i] = 0 end
  local function take(rows)
    for _, row in ipairs(rows) do
      local col = 1
      for _, cell in ipairs(row.cells) do
        local text = pandoc.utils.stringify(cell.contents)
        -- A spanning cell's text is shared out over the columns it covers,
        -- and its longest word is not anybody's minimum.
        local span = cell.col_span or 1
        local each = (utf8.len(text) or #text) / span
        for k = col, math.min(n, col + span - 1) do
          if each > w[k] then w[k] = each end
        end
        if span == 1 and col <= n then
          local lw = longest_word(text)
          if lw > words[col] then words[col] = lw end
        end
        col = col + span
      end
    end
  end
  take(tbl.head.rows)
  for _, body in ipairs(tbl.bodies) do
    take(body.head)
    take(body.body)
  end
  take(tbl.foot.rows)
  return w, words
end

-- A TABLE TOO WIDE FOR THE LINE gets column widths, which turns its columns
-- into wrapping paragraphs. Each column first gets its longest word, and what
-- is left of the line goes to the columns in proportion to the text they have
-- beyond that word. A table the source already gave widths to (a pipe table
-- with a long line, a grid or multiline table) is the author's layout and is
-- left alone.
function Table(tbl)
  for _, spec in ipairs(tbl.colspecs) do
    if spec[2] ~= nil then return nil end
  end
  local w, words = widest(tbl)
  local n = #w
  local natural, floor, extra = 0, 0, 0
  local base, more = {}, {}
  for i = 1, n do
    natural = natural + w[i] + WORD_PAD
    base[i] = words[i] + WORD_PAD
    more[i] = math.max(0, w[i] - words[i])
    floor = floor + base[i]
    extra = extra + more[i]
  end
  if natural <= LINE_CHARS then return nil end
  -- A table whose words alone nearly fill the line is set smaller, which is
  -- what a typesetter does with a wide table rather than break its headings.
  local size, line = "\\small", SMALL_CHARS
  if floor > SMALL_CHARS * 0.85 then size, line = "\\footnotesize", FOOTNOTE_CHARS end
  local spare = math.max(0, line - floor)
  local chars, sum = {}, 0
  for i = 1, n do
    chars[i] = base[i] + (extra > 0 and spare * more[i] / extra or 0)
    sum = sum + chars[i]
  end
  -- Words that do not fit even one to a column overflow whatever is done;
  -- shrinking every column by the same factor at least keeps them in order.
  for i = 1, n do
    tbl.colspecs[i] = { tbl.colspecs[i][1], chars[i] / sum }
  end
  return { pandoc.RawBlock("latex", "\\begingroup" .. size), tbl,
           pandoc.RawBlock("latex", "\\endgroup") }
end

-- Set when a code block is rewritten, and read by `Meta`, which pandoc runs
-- after every block.
local wants_fvextra = false

-- A CODE BLOCK WRAPS. fvextra's Verbatim breaks a line at the margin and marks
-- the break, and the text inside it is still taken literally.
function CodeBlock(block)
  if #block.classes > 0 then return nil end
  wants_fvextra = true
  return pandoc.RawBlock("latex",
    "\\begin{Verbatim}[breaklines,breakanywhere]\n" .. block.text
    .. "\n\\end{Verbatim}")
end

local ESCAPE = {
  ["\\"] = "\\textbackslash{}", ["{"] = "\\{", ["}"] = "\\}",
  ["$"] = "\\$", ["&"] = "\\&", ["#"] = "\\#", ["%"] = "\\%",
  ["^"] = "\\textasciicircum{}", ["~"] = "\\textasciitilde{}",
  ["_"] = "\\_",
}

-- The text, escaped for LaTeX, with a break allowed after each character in
-- `after` -- where a path or an identifier reads naturally across two lines.
local function breakable(text, after)
  local out = {}
  for ch in text:gmatch(utf8.charpattern) do
    out[#out + 1] = ESCAPE[ch] or ch
    if after[ch] then out[#out + 1] = "\\allowbreak{}" end
  end
  return table.concat(out)
end

local CODE_BREAKS = { ["/"] = true, ["_"] = true, ["."] = true, ["-"] = true }
-- Prose keeps its hyphenation; a bare path there breaks only at a slash or an
-- underscore, so a sentence's full stop never starts a line.
local PATH_BREAKS = { ["/"] = true, ["_"] = true }

-- LONG INLINE CODE MAY BREAK after a slash, an underscore, a dot or a hyphen.
function Code(code)
  if #code.text < LONG_CODE then return nil end
  return pandoc.RawInline("latex",
    "\\texttt{" .. breakable(code.text, CODE_BREAKS) .. "}")
end

-- A LONG PATH WRITTEN AS PROSE is one word to TeX, which will not break it, so
-- it sticks out past the margin of a justified paragraph.
function Str(str)
  if #str.text < LONG_CODE or not str.text:find("/", 1, true) then return nil end
  return pandoc.RawInline("latex", breakable(str.text, PATH_BREAKS))
end

-- fvextra, for the code blocks above, added to whatever the document's own
-- header asks for rather than in place of it. Only where a code block needs
-- it: fvextra loads lineno, and lineno breaks a longtable whose rows run long
-- ("Dimension too large"), which is the TRIPOD checklist.
function Meta(meta)
  if not wants_fvextra then return nil end
  local add = pandoc.RawBlock("latex", "\\usepackage{fvextra}")
  local have = meta["header-includes"]
  if have == nil then
    meta["header-includes"] = pandoc.MetaList({ pandoc.MetaBlocks({ add }) })
  elseif pandoc.utils.type(have) == "List" then
    have:insert(pandoc.MetaBlocks({ add }))
  else
    meta["header-includes"] = pandoc.MetaList({ have, pandoc.MetaBlocks({ add }) })
  end
  return meta
end
