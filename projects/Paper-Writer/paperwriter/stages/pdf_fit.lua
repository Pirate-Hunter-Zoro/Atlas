-- pdf_fit.lua -- keep a PDF's tables, figures, code and paths inside the page.
--
-- Pandoc's LaTeX writer leaves each of these to go wrong with no error:
--
--   * a SIMPLE table gets no column widths, so each column is as wide as its
--     longest cell and a six-column results table is wider than the page;
--   * a table the source gave widths to (a pipe table with a long line, a grid
--     or multiline table) takes them from its dashes, and a column whose dashes
--     are shorter than its longest word prints that word over the next column;
--   * a caption and a panel label are paragraphs of their own, so a page break
--     can fall between one and the table or image it names;
--   * a code block is `verbatim`, which never breaks a line, and a patient
--     narrative is one long line per field;
--   * inline code is `\texttt`, which never hyphenates, so a long file path
--     sticks out of a justified paragraph.
--
-- Only the PDF changes. A .docx lays its own tables out and wraps its own code,
-- and the journal copy must not be touched by a fix for the reading copy.
--
-- Two passes. The first measures tables on their source text and then makes
-- their cells breakable; the second rewrites code and paths everywhere else.
-- One pass would measure a cell after its text had become raw LaTeX, which
-- has no length.

if not FORMAT:match("latex") then
  return {}
end

-- The text width of pandoc's default page (article, 10pt, letter), in points.
local LINE_PT = 345
-- About as many characters of DejaVu Sans as that line holds at each face a
-- table is set in. A table whose cells fit the first is left at its natural
-- widths.
local LINE_CHARS = 62
local SMALL_CHARS = 68
local FOOTNOTE_CHARS = 76
local SCRIPT_CHARS = 88
-- \tabcolsep in points: LaTeX's, and the tighter one the smallest faces take.
-- It does not shrink with the face, so it costs a many-column table a lot.
local TABCOLSEP = 6
local TIGHT_TABCOLSEP = 3
-- Room a cell needs beyond its text when the table is left at natural widths.
local CELL_PAD = 3
-- Each column keeps room for its longest unbreakable piece plus this, because
-- a piece is never broken and one wider than its column prints over the next.
local WORD_PAD = 1
-- Bold DejaVu is wider than regular, and a heading is bold.
local BOLD = 1.1
-- Inline code shorter than this fits on any line and is left to pandoc.
local LONG_CODE = 24
-- A panel label ("A bge-small-en-v1.5") is a capital, a space and at most this
-- many characters in all.
local PANEL_LABEL = 160
-- Lines a table needs below its caption -- heading and first row -- before the
-- caption is worth starting on this page.
local TABLE_LEAD = 8
-- Lines a section heading takes, with the space above and below it.
local HEADING_LINES = 3
-- A ragged-right column fills about this much of its width before a word
-- wraps, and a table's rules and their padding cost about this many lines.
local WRAP_FILL = 0.8
local RULE_LINES = 1
-- Lines of body text the default page holds (\textheight over \baselineskip,
-- rounded down for the space round a paragraph).
local PAGE_LINES = 43
-- The default page's \textheight, in points, and the points in an inch.
local PAGE_PT = 550
local PT_PER_IN = 72.27

-- Set when a rewrite needs a package, and read by `Meta`, which runs last.
local wants_fvextra = false
local wants_needspace = false

local ESCAPE = {
  ["\\"] = "\\textbackslash{}", ["{"] = "\\{", ["}"] = "\\}",
  ["$"] = "\\$", ["&"] = "\\&", ["#"] = "\\#", ["%"] = "\\%",
  ["^"] = "\\textasciicircum{}", ["~"] = "\\textasciitilde{}",
  ["_"] = "\\_", ["|"] = "\\textbar{}",
  ["<"] = "\\textless{}", [">"] = "\\textgreater{}",
}

-- Whether `rule` lets a line break after the `i`th of `chars`: always (true),
-- never (nil), or when the function says so.
local function breaks(rule, chars, i)
  if type(rule) == "function" then return rule(chars, i) end
  return rule == true
end

-- The text, escaped for LaTeX, with a break allowed after each character in
-- `after` -- where a path or an identifier reads naturally across two lines.
local function breakable(text, after)
  local chars = {}
  for ch in text:gmatch(utf8.charpattern) do chars[#chars + 1] = ch end
  local out = {}
  for i, ch in ipairs(chars) do
    out[#out + 1] = ESCAPE[ch] or ch
    if breaks(after[ch], chars, i) then
      out[#out + 1] = "\\allowbreak{}"
    end
  end
  return table.concat(out)
end

local CODE_BREAKS = { ["/"] = true, ["_"] = true, ["."] = true, ["-"] = true }
-- A slash with another after it is the first of a URL's "//", and a line
-- ending "https:/" reads as a malformed address.
local function not_doubled(chars, i)
  return chars[i + 1] ~= "/"
end
-- Prose keeps its hyphenation; a bare path there breaks only at a slash or an
-- underscore, so a sentence's full stop never starts a line.
local PATH_BREAKS = { ["/"] = not_doubled, ["_"] = true }
-- Letters running from the `i`th of `chars` in direction `step`, counted up
-- to `need`.
local function letters(chars, i, step, need)
  local n = 0
  while n < need and chars[i] and chars[i]:match("^%a$") do
    n = n + 1
    i = i + step
  end
  return n
end

-- A slash between two words of three letters or more ("White/Caucasian").
-- "S/D", "N/A" and "46/297" stay whole: a line starting "/D" reads wrong.
local function between_words(chars, i)
  return letters(chars, i - 1, -1, 3) >= 3 and letters(chars, i + 1, 1, 3) >= 3
end

-- A table cell breaks a snake_case identifier after an underscore, and a pair
-- of words after the slash.
local CELL_BREAKS = { ["_"] = true, ["/"] = between_words }

-- The longest piece of `text` that cannot break, in characters: words split
-- where `CELL_BREAKS` lets them, after a hyphen, where TeX breaks by itself,
-- and, if `dashes`, after an en dash, where it also does. An interval
-- "(0.643–0.672)" is one piece or two depending on which is asked for.
local function longest_word(text, dashes)
  local most = 0
  for word in text:gmatch("%S+") do
    local chars = {}
    for ch in word:gmatch(utf8.charpattern) do chars[#chars + 1] = ch end
    local run = 0
    for i, ch in ipairs(chars) do
      run = run + 1
      if run > most then most = run end
      if ch == "-" or (dashes and ch == "–")
          or breaks(CELL_BREAKS[ch], chars, i) then
        run = 0
      end
    end
  end
  return most
end

local function is_bold(cell)
  local bold = false
  pandoc.Div(cell.contents):walk({ Strong = function() bold = true end })
  return bold
end

-- Per column: the longest cell, and the longest piece that cannot break with
-- and without a break at a dash, in characters, a bold piece counted at its
-- bold width.
local function widest(tbl)
  local n = #tbl.colspecs
  local w, whole, parts = {}, {}, {}
  for i = 1, n do w[i] = 0; whole[i] = 0; parts[i] = 0 end
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
          local scale = is_bold(cell) and BOLD or 1
          whole[col] = math.max(whole[col], longest_word(text, false) * scale)
          parts[col] = math.max(parts[col], longest_word(text, true) * scale)
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
  return w, whole, parts
end

-- The characters a row of `n` columns has for text at one face: the line, less
-- the space between columns.
local function room(chars, n, sep)
  return chars * (1 - 2 * (n - 1) * sep / LINE_PT)
end

-- The faces a widened table is tried in, smallest last. \small is taken only
-- with room to spare, because a table set small whose words exactly fill it
-- wraps every cell.
local SMALL = { size = "\\small", chars = SMALL_CHARS, sep = TABCOLSEP, fill = 0.85 }
local FOOTNOTE = { size = "\\footnotesize", chars = FOOTNOTE_CHARS, sep = TABCOLSEP, fill = 1 }
local TIGHT = { size = "\\footnotesize", chars = FOOTNOTE_CHARS, sep = TIGHT_TABCOLSEP, fill = 1 }
local SCRIPT = { size = "\\scriptsize", chars = SCRIPT_CHARS, sep = TIGHT_TABCOLSEP, fill = 1 }
-- Tried in order; the first face whose columns hold every piece is used.
-- Whole intervals first, at the faces a reader reads without effort, and only
-- then intervals broken at their dash, which costs a third line per cell;
-- \scriptsize is the last resort before words overprint.
local TRIES = {
  { "whole", SMALL }, { "whole", FOOTNOTE }, { "whole", TIGHT },
  { "parts", SMALL }, { "parts", FOOTNOTE }, { "parts", TIGHT },
  { "parts", SCRIPT },
}

local function breakable_cells(tbl)
  return tbl:walk({
    Str = function(str)
      if str.text:find("_", 1, true) or str.text:find("/%a") then
        return pandoc.RawInline("latex", breakable(str.text, CELL_BREAKS))
      end
    end,
    Code = function(code)
      if code.text:find("[_/]") then
        return pandoc.RawInline("latex",
          "\\texttt{" .. breakable(code.text, CODE_BREAKS) .. "}")
      end
    end,
  })
end

-- A TABLE TOO WIDE FOR THE LINE gets column widths, which turns its columns
-- into wrapping paragraphs. Each column first gets its longest unbreakable
-- piece, and what is left of the line goes to the columns in proportion to
-- the text they have beyond it. A table the source gave widths to keeps them
-- while every column holds its longest piece; one that does not is laid out
-- by the same rule, since the dashes of a pipe table were never a layout.
local function Table(tbl)
  local w, whole, parts = widest(tbl)
  local pieces = { whole = whole, parts = parts }
  local n = #w
  local function floor_of(words)
    local sum = 0
    for i = 1, n do sum = sum + words[i] + WORD_PAD end
    return sum
  end
  local natural = 0
  for i = 1, n do natural = natural + w[i] + CELL_PAD end
  local given = false
  for _, spec in ipairs(tbl.colspecs) do
    if spec[2] ~= nil then given = true end
  end
  if given then
    -- At the source's widths TeX may break an interval at its dash, so only
    -- a piece it cannot break has to fit.
    local line = room(LINE_CHARS, n, TABCOLSEP)
    local holds = true
    for i, spec in ipairs(tbl.colspecs) do
      if spec[2] * line < parts[i] + WORD_PAD then holds = false end
    end
    if holds then return breakable_cells(tbl) end
  end
  if natural <= LINE_CHARS then
    for i, spec in ipairs(tbl.colspecs) do
      tbl.colspecs[i] = { spec[1], nil }
    end
    return breakable_cells(tbl)
  end
  local face, words = SCRIPT, parts
  for _, try in ipairs(TRIES) do
    local f = try[2]
    if floor_of(pieces[try[1]]) <= room(f.chars, n, f.sep) * f.fill then
      face, words = f, pieces[try[1]]
      break
    end
  end
  local floor, extra = floor_of(words), 0
  local more = {}
  for i = 1, n do
    more[i] = math.max(0, w[i] - words[i])
    extra = extra + more[i]
  end
  local spare = math.max(0, room(face.chars, n, face.sep) - floor)
  local chars, sum = {}, 0
  for i = 1, n do
    chars[i] = words[i] + WORD_PAD + (extra > 0 and spare * more[i] / extra or 0)
    sum = sum + chars[i]
  end
  -- Words that do not fit even the smallest face overflow whatever is done;
  -- shrinking every column by the same factor at least keeps them in order.
  for i = 1, n do
    tbl.colspecs[i] = { tbl.colspecs[i][1], chars[i] / sum }
  end
  local open = "\\begingroup" .. face.size
  if face.sep ~= TABCOLSEP then
    open = open .. "\\setlength{\\tabcolsep}{" .. face.sep .. "pt}"
  end
  return { pandoc.RawBlock("latex", open), breakable_cells(tbl),
           pandoc.RawBlock("latex", "\\endgroup") }
end

local function only_images(inlines)
  local images = 0
  for _, el in ipairs(inlines) do
    if el.t == "Image" then
      images = images + 1
    elseif el.t ~= "Space" and el.t ~= "SoftBreak" and el.t ~= "LineBreak" then
      return false
    end
  end
  return images > 0
end

local function is_image(block)
  if block == nil then return false end
  if block.t == "Figure" then return true end
  return (block.t == "Para" or block.t == "Plain") and only_images(block.content)
end

local function is_caption(block)
  if block == nil or block.t ~= "Para" then return false end
  local text = pandoc.utils.stringify(block)
  return text:match("^Table %u?%d+%.") ~= nil or text:match("^Figure %u?%d+%.") ~= nil
end

local function is_panel_label(block)
  if block == nil or (block.t ~= "Para" and block.t ~= "Plain") then
    return false
  end
  local text = pandoc.utils.stringify(block)
  return (utf8.len(text) or #text) <= PANEL_LABEL and text:match("^%u%s+%S") ~= nil
end

-- A table, or the group `Table` above opened around one.
local function is_table(blocks, i)
  local block = blocks[i]
  if block == nil then return false end
  if block.t == "Table" then return true end
  return block.t == "RawBlock" and block.text:match("^\\begingroup") ~= nil
     and blocks[i + 1] ~= nil and blocks[i + 1].t == "Table"
end

local function latex(text) return pandoc.RawBlock("latex", text) end

local function lines_of(block)
  local text = pandoc.utils.stringify(block)
  return math.ceil((utf8.len(text) or #text) / LINE_CHARS)
end

-- A width pandoc reads, in inches; nil for a unit this does not know.
local INCHES = { ["in"] = 1, cm = 1 / 2.54, mm = 1 / 25.4, pt = 1 / PT_PER_IN }

local function inches(width)
  local percent = width:match("^([%d.]+)%%$")
  if percent then
    return tonumber(percent) / 100 * LINE_PT / PT_PER_IN
  end
  local number, unit = width:match("^([%d.]+)(%a%a)$")
  if number and INCHES[unit] and tonumber(number) then
    return tonumber(number) * INCHES[unit]
  end
end

-- An image may be as tall as the page, and one held to its label or caption
-- then has nothing to break against: TeX ships empty pages until it runs out
-- of page numbers. So an image kept with `lines` of text is narrowed until it
-- is no taller than the page less those lines. The Image stays an Image, so
-- pandoc still finds its file on the resource path and copies it where TeX
-- runs; only its width changes. An image with no width, a height of its own,
-- or a file pandoc cannot read is left as it is.
local function leave_room(block, lines)
  if block.t ~= "Para" and block.t ~= "Plain" then return block end
  local room_in = (1 - (lines + 1) / PAGE_LINES) * PAGE_PT / PT_PER_IN
  return block:walk({
    Image = function(image)
      local width = image.attributes.width
      if width == nil or image.attributes.height ~= nil then return nil end
      local given = inches(width)
      if given == nil then return nil end
      local ok, _, contents = pcall(pandoc.mediabag.fetch, image.src)
      if not ok or contents == nil then return nil end
      local sized, size = pcall(pandoc.image.size, contents)
      if not sized or not size.width or size.width == 0 then return nil end
      -- Height over width as printed, which differs from the pixels' when the
      -- file's two resolutions do.
      local tall = (size.height / (size.dpi_vert or 72))
                 / (size.width / (size.dpi_horz or 72))
      if given * tall <= room_in then return nil end
      image.attributes.width = string.format("%.2fin",
        math.floor(room_in / tall * 100) / 100)
      return image
    end,
  })
end

-- Lines, at the body face, that a table's heading and first row need: each
-- cell's text over the characters its share of the line holds at \small,
-- tallest cell per row. Never less than TABLE_LEAD, never more than a page
-- less the heading. An estimate on the high side, since \small lines are
-- shorter than the body's.
local function lead_lines(tbl)
  local n = #tbl.colspecs
  local function row_lines(row)
    local most, col = 1, 1
    for _, cell in ipairs(row.cells) do
      local span = cell.col_span or 1
      local share = 0
      for k = col, math.min(n, col + span - 1) do
        local w = tbl.colspecs[k][2]
        share = share + ((type(w) == "number" and w > 0) and w or 1 / n)
      end
      local text = pandoc.utils.stringify(cell.contents)
      local chars = math.max(1, share * SMALL_CHARS * WRAP_FILL)
      most = math.max(most, math.ceil((utf8.len(text) or #text) / chars))
      col = col + span
    end
    return most
  end
  local lines = RULE_LINES
  for _, row in ipairs(tbl.head.rows) do lines = lines + row_lines(row) end
  local first = tbl.bodies[1] and tbl.bodies[1].body[1]
  if first then lines = lines + row_lines(first) end
  return math.min(PAGE_LINES - HEADING_LINES, math.max(TABLE_LEAD, lines))
end

-- One unbreakable box holding `blocks`, which the page break goes around.
local function unbroken(out, blocks)
  out:insert(latex("\\par\\noindent\\begin{minipage}{\\linewidth}"))
  for k, block in ipairs(blocks) do
    if k > 1 then out:insert(latex("\\smallskip")) end
    out:insert(block)
  end
  out:insert(latex("\\end{minipage}\\par"))
end

-- A CAPTION OR A PANEL LABEL STAYS WITH WHAT IT NAMES.
--
--   * A panel label and the image after it are one box, so the label is never
--     the last line of a page with its panel on the next, and a two-line label
--     never splits.
--   * A caption before an image is boxed with it the same way, unless an
--     image comes before it too: then it is that image's caption, and a chain
--     of image, caption and image held together can outgrow the page.
--   * A caption before a table asks, with needspace's \Needspace, for room
--     for itself and the table's first rows, or starts a new page. A box
--     cannot hold a longtable, and a \nopagebreak cannot either: longtable
--     opens with a break of its own. Not the package's \needspace, whose
--     break is decided only once the longtable has taken over the output
--     routine, which then prints the table's heading above the caption.
--   * A heading directly above a table asks for the same room, because
--     longtable's own opening break would otherwise leave the heading as
--     the last line of a page.
--   * A caption after an image may not be broken from it.
--
-- Each image kept this way is capped so that it and its text fit one page.
local function Blocks(blocks)
  local out = pandoc.Blocks({})
  local i = 1
  local after_image = false
  while i <= #blocks do
    local block, nxt = blocks[i], blocks[i + 1]
    local image = false
    if (is_panel_label(block) or (is_caption(block) and not after_image))
        and is_image(nxt) then
      local lines = lines_of(block)
      local after = is_caption(blocks[i + 2]) and lines_of(blocks[i + 2]) or 0
      unbroken(out, { block, leave_room(nxt, lines + after) })
      i = i + 2
      image = true
      if after > 0 then out:insert(latex("\\nopagebreak")) end
    elseif block.t == "Header" and is_table(blocks, i + 1) then
      wants_needspace = true
      local tbl = blocks[i + 1].t == "Table" and blocks[i + 1] or blocks[i + 2]
      out:insert(latex(string.format("\\Needspace{%d\\baselineskip}",
                                     HEADING_LINES + lead_lines(tbl))))
      out:insert(block)
      i = i + 1
    elseif is_caption(block) and is_table(blocks, i + 1) then
      wants_needspace = true
      out:insert(latex(string.format("\\Needspace{%d\\baselineskip}",
                                     lines_of(block) + TABLE_LEAD)))
      out:insert(block)
      i = i + 1
    elseif is_image(block) and is_caption(nxt) then
      out:insert(leave_room(block, lines_of(nxt)))
      out:insert(latex("\\nopagebreak"))
      i = i + 1
      image = true
    else
      out:insert(block)
      i = i + 1
      image = is_image(block)
    end
    after_image = image
  end
  return out
end

-- A CODE BLOCK WRAPS. fvextra's Verbatim breaks a line at the margin and marks
-- the break, and the text inside it is still taken literally.
local function CodeBlock(block)
  if #block.classes > 0 then return nil end
  wants_fvextra = true
  return pandoc.RawBlock("latex",
    "\\begin{Verbatim}[breaklines,breakanywhere]\n" .. block.text
    .. "\n\\end{Verbatim}")
end

-- LONG INLINE CODE MAY BREAK after a slash, an underscore, a dot or a hyphen.
local function Code(code)
  if #code.text < LONG_CODE then return nil end
  return pandoc.RawInline("latex",
    "\\texttt{" .. breakable(code.text, CODE_BREAKS) .. "}")
end

-- A LONG PATH WRITTEN AS PROSE is one word to TeX, which will not break it, so
-- it sticks out past the margin of a justified paragraph.
local function Str(str)
  if #str.text < LONG_CODE or not str.text:find("/", 1, true) then return nil end
  return pandoc.RawInline("latex", breakable(str.text, PATH_BREAKS))
end

-- The packages the rewrites above need, added to whatever the document's own
-- header asks for rather than in place of it, and only where used: fvextra
-- loads lineno, and lineno breaks a longtable whose rows run long ("Dimension
-- too large"), which is the TRIPOD checklist.
local function Meta(meta)
  local adds = {}
  if wants_fvextra then adds[#adds + 1] = "\\usepackage{fvextra}" end
  if wants_needspace then adds[#adds + 1] = "\\usepackage{needspace}" end
  if #adds == 0 then return nil end
  local have = meta["header-includes"]
  if have == nil then
    have = pandoc.MetaList({})
  elseif pandoc.utils.type(have) ~= "List" then
    have = pandoc.MetaList({ have })
  end
  for _, add in ipairs(adds) do
    have:insert(pandoc.MetaBlocks({ pandoc.RawBlock("latex", add) }))
  end
  meta["header-includes"] = have
  return meta
end

return {
  { Table = Table, Blocks = Blocks },
  { CodeBlock = CodeBlock, Code = Code, Str = Str, Meta = Meta },
}
