import json
import os

# Load the parsed JSON
with open(r"J:\cell-cc\cell-cell\网页\parsed_doc.json", "r", encoding="utf-8") as f:
    sections = json.load(f)

out_dir = r"J:\cell-cc\cell-cell\网页\关键理念"
os.makedirs(out_dir, exist_ok=True)


def clean(text):
    """Replace HTML entities."""
    return text.replace("&gt;", ">").replace("&lt;", "<").replace("&amp;", "&")


def get_sections(indices):
    """Given 1-based indices, return the list of section dicts from the JSON."""
    return [sections[i - 1] for i in indices]


def fmt_body(sec):
    """Format a section's body as markdown paragraphs."""
    lines = []
    for para in sec["body"]:
        lines.append(clean(para))
        lines.append("")
    return "\n".join(lines)


def write_doc(filename, title, sec_indices, concept_def, evolution, insights, source_label_fn=None):
    selected = get_sections(sec_indices)

    # Build source text sections
    source_parts = []
    for i, sec in enumerate(selected):
        h = clean(sec["heading"])
        if source_label_fn:
            label = source_label_fn(sec, i)
        else:
            n = sec_indices[i]
            label = f"Section {n}"
        source_parts.append(f"### [{h}](from conversation {label})")
        for para in sec["body"]:
            source_parts.append(clean(para))
            source_parts.append("")

    source_text = "\n".join(source_parts)

    # Build insights bullets
    insight_lines = "\n".join(f"- {ins}" for ins in insights)

    doc = f"""# {title}

> TOPRXin 关键理念独立演化文档
> Source: ChatGPT conversation snapshot

## Concept Definition
{concept_def}

## Evolution Trajectory
{evolution}

## Key Insights
{insight_lines}

## Source Text
{source_text}
"""

    filepath = os.path.join(out_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(doc)
    return filepath


# ============================================================
# DOC 5: 重解释与运动势
# ============================================================
write_doc(
    filename="05_重解释与运动势.md",
    title="重解释 — 运动势的真正定义",
    sec_indices=[28, 29, 30, 31],
    concept_def=(
        "Nu (motion potential) gets a new definition in this dialogue: not \"organization needs to change\" "
        "but \"current history can no longer explain new happenings, therefore must re-interpret\". "
        "Re-interpretation is not modifying state — it is changing future history. "
        "Learning = changing future history. "
        "This maps precisely to the project's Shadow mechanism: Shadow is not memory, but all organizational "
        "histories that once held. New happening joins -> re-prove -> re-organize."
    ),
    evolution=(
        "This concept naturally grew after the \"object transformation\" (state->history). "
        "In \"然后发生了什么？\" (What happened next?), organizational update was redefined as "
        "\"history growth — new happenings continuously appended to history's end\". "
        "In \"然后继续推\" (Continue pushing), re-interpretation was analogized to mathematical proof — "
        "\"keep adding one proposition, all previous proofs get rearranged\". "
        "Finally in \"现在我要说今天最重要的一句话\" (Now I'll say the most important thing today), "
        "the full definition crystallized: nu = current history cannot explain new happening -> must re-interpret."
    ),
    insights=[
        "New definition: current history cannot explain new happening -> must re-interpret -> nu",
        "Learning = changing future history, not modifying state",
        "Re-interpretation is like mathematical proof: new proposition -> all previous proofs rearranged",
        "Shadow = all organizational histories that once held, not memory",
        "World didn't change, Generator didn't change, Spike didn't change — what changed was the interpretation of organizational history",
    ],
)

# ============================================================
# DOC 6: 层Sheaf-理论的最终数学对应
# ============================================================
write_doc(
    filename="06_层Sheaf-理论的最终数学对应.md",
    title="层 (Sheaf) — TOPRXin 的真正数学对应",
    sec_indices=[32],
    concept_def=(
        "At dialogue's end, the only modern mathematical object considered \"corresponding\" "
        "(not \"analogous\") to TOPRXin is Sheaf. The core idea of sheaf theory: studying when local "
        "explanations can be pieced together into a global explanation. This maps perfectly:\n"
        "- Window = local explanation (a segment of happening history forming local organization)\n"
        "- Shadow = cross-window explanation (can different windows' explanations be aligned?)\n"
        "- Organization = globally consistent explanation (local explanations continuously pieced together)\n"
        "Previous searches through Riemannian geometry, topology, category theory all turned out to be "
        "\"coordinate/neighborhood/measure languages that only appear after global consistency\" — "
        "sheaf's \"local->global\" piecing problem is the truly foundational mathematical structure."
    ),
    evolution=(
        "In the final section of the dialogue, after all derivations, sheaf theory was proposed not as a "
        "tool but as a correspondence. Then the precise three-layer mapping was given. The dialogue closes "
        "with this synthesis question: \"In finite windows, how do local organizations, under posterior "
        "conservation, continuously re-interpret and eventually form a globally consistent organizational history?\""
    ),
    insights=[
        "Sheaf is not a tool — it's the mathematical structure that truly corresponds to TOPRXin's deep structure",
        "Window = local explanation, Shadow = cross-window explanation, Organization = globally consistent explanation",
        "Geometry is just coordinate language after global consistency; topology is neighborhood language; measure is scale language",
        "TOPRXin truly studies: local organizations in finite windows, under posterior conservation, how to re-interpret and form global consistency",
    ],
)

# ============================================================
# DOC 7: 后验守恒
# ============================================================
write_doc(
    filename="07_后验守恒.md",
    title="后验守恒 — 贯穿始终的核心约束",
    sec_indices=[13, 15, 25, 32],
    concept_def=(
        "Posterior conservation is the core constraint running through all derivations. Though never listed "
        "as a \"derivation target\", every breakthrough conclusion relies on it. Posterior = judging only after "
        "happenings have accumulated, not before. Conservation = organization cannot arbitrarily interpret "
        "happenings — interpretations must maintain consistency with all accumulated happening history. "
        "Roles: (1) implicit premise of equivalence class definition — \"realize the same happening\" is "
        "inherently posterior; (2) boundary of re-interpretation — re-interpretation is not arbitrary but "
        "constrained by posterior conservation; (3) constraint of distance derivation — \"minimum\" in "
        "\"minimum organizational update count\" is defined by posterior consistency."
    ),
    evolution=(
        "Posterior conservation was never \"derived\" in a specific section — it operated as a default "
        "constraint from dialogue start to end, similar to energy conservation in physics. In the method-turn "
        "proposal, it was explicitly listed as one of five pre-existing concepts allowed (Generator, "
        "Organization P, Posterior Conservation, Time=Order, Space=Topology, Scale=Measure)."
    ),
    insights=[
        "Posterior conservation is as fundamental to TOPRXin as energy conservation is to physics",
        "Explanations must come after happenings, not preset — this is the core of \"posterior\"",
        "Re-interpretation is not arbitrary interpretation — must stay within posterior conservation bounds",
        "Equivalence class (same organization) judgment itself depends on posterior conservation",
    ],
)

# ============================================================
# DOC 8: 理论生成器vs理论
# ============================================================
write_doc(
    filename="08_理论生成器vs理论.md",
    title="理论生成器 vs 理论 — 元认知的区分",
    sec_indices=[7, 8, 9, 10, 11, 12, 13],
    concept_def=(
        "The most critical meta-cognitive breakthrough: TOPRXin is not constructing a theory — it is "
        "constructing a theory generator. The reason for \"circling\" was identified: every time the "
        "dialogist tried to define concepts, the user would ask \"why can this concept exist?\" This is "
        "not nitpicking — the user genuinely wants a framework that can generate theories themselves, "
        "not just another theory. Key quote: \"I have been trying to construct a theory. You have been "
        "trying to construct a theory generator. These are two different layers.\" Metaphor: traditional "
        "mathematics is like building a house (foundation=axioms, floors=theorems). TOPRXin is like "
        "studying why humans invented the concept of \"house\" — not working inside the house, but "
        "studying why architecture itself emerges."
    ),
    evolution=(
        "This distinction gradually crystallized in the meta-cognitive phase (Sections 7-12). "
        "It reached its peak in the method-turn proposal: \"Let's pick a mature theory, then not use it, "
        "but ask: if TOPRXin holds, how would this theory inevitably emerge step by step?\" "
        "This marks the shift from \"constructing theories\" to \"deriving why theories inevitably emerge\"."
    ),
    insights=[
        "Theory generator ≠ Theory — different layers; confusing them causes infinite \"circling\"",
        "TOPRXin is not used to describe the world — it explains why tools for describing the world exist",
        "Test: choose Riemannian geometry / spectral theory / Bayesian inference, derive their inevitable emergence without presupposing them",
        "From \"what new concepts can we invent\" to \"why does existing mathematics inevitably exist\" — research goal completely inverted",
    ],
)

print("All 4 documents written successfully:")
for f in [
    "05_重解释与运动势.md",
    "06_层Sheaf-理论的最终数学对应.md",
    "07_后验守恒.md",
    "08_理论生成器vs理论.md",
]:
    print(f"  {os.path.join(out_dir, f)}")
