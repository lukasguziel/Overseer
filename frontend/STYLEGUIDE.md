# Style guide — Scene Organizer web UI

The vocabulary of the UI: every reusable visual building block, its name, and
the markup that produces it. **One block = one CSS class = one look.** When a
new spot needs an existing block, reuse the class and change only the text —
never fork a near-copy under a new name (that is how we ended up with
`.misc-sec` and `.rule-group-head` being the same divider twice).

Rules of the road:

- **Name by what it IS, not where it first appeared.** `.misc-sec` was named
  after the Misc tab and then spread to three other tabs; the name became a lie.
- **Keep domain words out of class names.** "Rule" means the rule engine in this
  project (`rules.py`, `GroupRule`). A divider is not a rule.
- **Variants are modifiers, not new classes**: `.section-head.sm`, not
  `.section-head-small`.
- New block? Add it here in the same shape: what it is, markup, variants.

## Where a style lives

A block's CSS sits **next to whatever owns it**, so a component can be read,
moved or deleted in one piece:

| CSS | Lives in | Because |
| --- | --- | --- |
| classes only one component ever renders | `components/<Name>.css`, imported by `<Name>.tsx` | the component owns its look — delete the component, the CSS goes with it |
| classes only one tab uses | `tabs/<name>.css`, imported by that tab | same, one level up |
| shared primitives (`.section-head`, `.mini`, `.card`, tokens) | `src/styles.css` | many places use them *without* any component — their look must not depend on some unrelated import happening to run |

The test: **does anything outside this component use the class?** If yes, it is
a primitive and belongs in `styles.css`. If no, it belongs to the component.
That is why `.section-intro` moved into `components/SectionIntro.css` while
`.section-head` — used by 15 places that never import the component — stayed
global.

Vite bundles all imported CSS into one file, so this is purely about where a
human finds it; there is no runtime cost.

---

## Section head — `.section-head`

A label with a rule/line running to the far edge. The one divider of the app:
it opens a section, whether that is an area of a tab or a group of controls in
a sidebar.

```jsx
<div className="section-head"><span>Rename rules</span></div>
```

| Variant | Where | Look |
| --- | --- | --- |
| `.section-head` | content width (tab intro, area dividers) | 11px uppercase |
| `.section-head sm` | inside a sidebar (`.wb-side`) | 10px uppercase, tighter margins |

The line is drawn by `::after`, so it needs no markup and always sits last.
Extra children (a count, a small button) go between the label and the line:

```jsx
<div className="section-head sm">
  <span>Resolution</span>
  <button className="mini">Reset</button>
</div>
```

A bare `.section-head` is for a section that needs no explanation (a group of
controls in a sidebar). When the area *does* need one, use `SectionIntro`.

---

## Section intro — `<SectionIntro>` / `.section-intro`

A section head plus the one-line description of what the area is for. **Always
the component, never hand-written markup** — that is what let the old
`sec-band` copies drift apart.

```jsx
<SectionIntro title="Rename rules"
  desc="Set the naming convention on the left; every rename is previewed on the right." />

<SectionIntro lead title="Textures" desc="Every map the scene references …" />
```

| Prop | Effect |
| --- | --- |
| `title` | the section head's label |
| `desc` | one line: what this area is for, in the artist's language |
| `lead` | this intro opens a whole tab → adds its own bottom gap (`.section-intro.lead`) |

Without `lead` the intro sits inside a `.stacked` tab and is spaced by the
parent's flex gap. `App.tsx` renders the per-tab intro from `TAB_INTRO`; a tab
only calls `SectionIntro` itself when it has several titled areas (Naming:
"Rename rules" + "Cleanup").

---

## Sidebar text hierarchy

Four levels, loudest first. Pick by rank, not by taste — if a new label looks
too loud, it is probably one rank too high.

| Rank | Class | Look | Use for |
| --- | --- | --- | --- |
| 1 | `.wb-side h3`, `.card-head h3` | uppercase 12px, `--dim2` | the panel's or card's title, once at the top |
| 2 | `.section-head sm` | uppercase 10px, `--dim2`, with a line | a group of controls |
| 3 | `.side-action-title` | sentence case 13px, `--dim` | one single action inside a group |
| 4 | `.hint-sm`, `.example` | 12px, `--dim2` / `--dim` | explanation, status |

**Rank is carried by case and size, not by brightness.** Titles are uppercase
with letter-spacing — that already separates them from body text, so they use
the same tertiary colour as the description underneath. A brighter title
shouts over the very content it introduces. `.side-action-title` is likewise a
*label*, not a heading.

The bright `--text` is reserved for the content itself: object names, values,
numbers — the things the artist actually reads.

### One action — `.side-action`

Wrap every runnable action in a sidebar in this block. It fixes the reading
order, and a column of actions stays scannable instead of turning into a pile
of buttons:

```html
<div class="side-action">
  <p class="side-action-title">What this does</p>   <!-- name it in plain words -->
  <p class="hint-sm">One sentence: what changes, on what.</p>
  <input class="nl-input" …>                       <!-- optional: input it needs -->
  <button class="ghost sm">Run it (12)</button>    <!-- ALWAYS last -->
</div>
```

The button goes **last**, never above its own description — the artist reads
what happens, then commits. Group related actions under a `.section-head sm`.
Name actions neutrally: `Make relative` / `Make absolute`, not `Fix paths` —
a preference is not a defect, and the UI must not call the user's pipeline wrong.

---

## Accepted-as-is — `<AcceptedSection>`

The card at the foot of every worklist area listing what the artist accepted
as-is. One component, seven usages (Naming, Layers, Structure, Translate,
Files, Materials ×2) — never rebuild it per tab.

Its shape is the pattern for **any collapsible area**:

1. `<SectionIntro>` — the title and the one-line explanation, always visible.
2. one framed toggle (`.kept-toggle`) — the only affordance, so it must *look*
   like a control: border, hover, and a caret that rotates when open.
3. the entries — **only** the results live behind the fold.

Never hide the explanation inside the fold, and never make a bare text label
the toggle: a heading-shaped button reads as a heading and nobody clicks it.

---

## Empty note — `.empty-note`

The one-line message that stands in for a list's content: nothing found, still
loading, scan failed.

```jsx
<div className="empty-note">No phong tags in the scene.</div>
<div className="empty-note mid">Every polygon object has a Phong tag 🎉</div>
```

| Variant | Layout |
| --- | --- |
| `.empty-note` | flush left, tight padding — inside a card, in place of a list |
| `.empty-note mid` | centred, 48px padding — fills the big preview panel of a `Workbench` |

**`mid` changes the layout, never the type.** Both read in the same 12px
tertiary colour as a description — an empty state is an aside, not content.
That is what went wrong before: the workbench version was brighter (`--dim`)
and the in-card version darker, so the same sentence looked like two different
things depending on where it appeared.

No left padding on the flush variant — it must line up with the heading of the
area it replaces, or the empty state looks indented against the real content.

Not to be confused with `EmptyState`, the big call-to-action card shown when a
whole tab has no data yet ("Run an analysis").

---

## Buttons

| Class | Look | Use for |
| --- | --- | --- |
| `<ActionButton>` / `.act` | 10px bold **UPPERCASE**, compact grey chip | every action in a listing / preview view (Relink, Select in C4D, Keep all as-is, Delete all) |
| `.ghost` | full-size, quiet outline | a `.side-action` in a sidebar, where the button spans the panel |
| `.apply` | green outline fill | the confirm button INSIDE a modal — the point of no return |

### Action button — `<ActionButton>`

**The** button of the app. Always the component, never a hand-rolled
`<button className="mini">`:

```jsx
<ActionButton onClick={selectInC4D}>Select in C4D</ActionButton>
<ActionButton tone="go" disabled={busy} onClick={relink}>Relink 12</ActionButton>
<ActionButton tone="danger" onClick={deleteAll}>Delete all unused</ActionButton>
```

**The resting state is always the same quiet grey.** An action must not shout
before the artist has decided to run it, and a row of actions has to read as a
row — not as a traffic light. What differs is only the **hover**, and only as a
tint:

| Tone | Hover | The action… |
| --- | --- | --- |
| `neutral` (default) | lifts out of the panel, no colour | changes **nothing** in the scene: Select in C4D, Browse, Accept as-is, Clear log |
| `go` | green tint | **builds or repairs**: Apply, Relink, Add phong tag, Make relative, Measure |
| `danger` | red tint | **removes**: Delete all unused, Delete duplicates, Clear dead references |

Pick the tone by **consequence, not by importance**. "Delete all unused
materials" is the batch action of its panel, but it destroys — it is `danger`,
not the loud primary. "Keep all as-is" sounds passive but is the panel's other
big button — it is still `neutral`, because the scene does not change.

**No accent-blue hover.** A full accent fill on hover repaints the button and
reads like the state changed rather than like a preview of what a click will
do. The hover is a whisper, not an announcement.

`Workbench` renders the batch pair for every worklist (`onApply` + `onAcceptAll`)
with exactly these tones — pass `applyTone="danger"` when the batch apply
deletes (Materials: "Delete all", Tags: "Delete all duplicates").

---

## Data grid — `.dg-*`

The one data table of the app (textures on Materials, external files on Files).
Rows are buttons: clicking one selects its owner in Cinema 4D.

```jsx
<div className="dg-table">
  <div className="dg-tr dg-thead cols-files dg-actionable"> … </div>
  <div className="dg-tr dg-click cols-files dg-actionable"> … </div>
</div>
```

| Class | What it is |
| --- | --- |
| `.dg-table` | the column stack |
| `.dg-tr` | one row: grid, padding, hairline — **no columns** |
| `.dg-thead` | the header row's typography |
| `.dg-click` | the row is a button (hover, no chrome) |
| `.dg-cut` / `.dg-cell-file` / `.dg-cell-path` | cell helpers (ellipsis, icon+text) |

**The columns are the only per-table part**: a `cols-*` modifier carries the
`grid-template-columns` and nothing else — `.cols-tex` in `styles.css`,
`.cols-files` in `tabs/files.css`. `.dg-actionable` is the variant whose rows
carry a per-row decision slot (…/=/✕); it must sit on **every** row of that
table *and on the header*, or the columns drift apart. Never fork the block
under a new prefix (that is how `.fa-*` became a second copy of `.tex-*`).

---

## Pill — `.pill`

One word about the thing next to it: `missing`, `unused`, `cached`, a count.
The variant carries the meaning, per the colour table below.

```jsx
<span className="pill missing">missing</span>
<span className="pill">{type.count}</span>
```

Variants: `.unused`, `.missing`, `.fixable`, `.resized` (shared) plus per-tab
ones on the same base (`.sim-ok`, `.sim-warn`, `.sim-dim`, `.sim-kind` in
`tabs/sims.css`). Not to be confused with `.badge`, the amber todo count on a
tab.

---

## Filter chip — `.chip-btn`

A toggle that narrows the list next to it (resolution, kind, channel, angle
preset). `.on` = active, `<em>` = the count.

```jsx
<div className="chip-row side">
  <button className={'chip-btn' + (on ? ' on' : '')}>4K <em>12</em></button>
</div>
```

| Class | Where |
| --- | --- |
| `.chip-row` | the row of chips (content width) |
| `.chip-row.side` | the same row inside a sidebar (wraps, tighter) |
| `.chip-btn.tf-warn` | count tinted amber while the filter is off |

---

## Select in C4D — `button.mini`

Every "select the matching objects in Cinema 4D" action is the same button —
`button.mini`, nothing else. It used to be four different looks (a one-off
`.tags-select-btn`, `.mini`, a `.ghost` with a font-size override); one verb
gets one look.

---

## Checkbox

Every checkbox in the app is the same drawn box — 14px, accent fill, dark tick.
There is **no class**: the style hangs on `input[type=checkbox]`, so a plain
checkbox is automatically right and nobody has to remember a class name.

```jsx
<label className="check">
  <input type="checkbox" checked={onlyGeo} onChange={…} /> Only geometry
</label>
```

Three states, all drawn: **checked** (tick), **indeterminate** (dash — the
"select all" box when only some rows are ticked; set it via a ref, as
`AssetsTab` does), **disabled** (faded).

`label.check` is the row that pairs a box with its text (flex, 8px gap).

---

## Colour meaning

Colour carries meaning; do not spend it on decoration.

| Token | Means |
| --- | --- |
| `--err` | a defect — something is broken (missing file) |
| `--warn` | needs a decision, still functional |
| `--apply` | healthy / will be applied |
| `--accent` | the interactive accent (hover, active state) |
| `--text` / `--dim` / `--dim2` | text ranks: primary, secondary, tertiary |

A hint that merely says "you cannot do this yet" is **not** a warning — it is
tertiary text (`.hint-sm`). Warning colour is reserved for things the artist
must act on.
