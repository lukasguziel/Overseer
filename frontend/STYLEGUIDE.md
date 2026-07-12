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
| `.mini` | 10px bold **UPPERCASE**, compact, accent on hover | actions in a card head or sidebar (Relink, Accept all, Make relative) |
| `.ghost` | full-size, quiet outline | secondary actions that carry weight |
| `.primary` | accent fill | the one action a screen is about |

`button.mini` is the default for narrow, repeated actions — it stays small and
does not stretch, so several fit next to each other.

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
