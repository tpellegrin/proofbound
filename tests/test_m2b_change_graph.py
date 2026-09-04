"""The declared change graph: authority states topology, Python enforces it.

M2A validates relationships that were already recorded. It has no notion of completeness,
because nothing ever declared what complete means. The graph supplies exactly that
statement — and nothing else.

The boundary this file exists to defend:

    artifact validity  !=  graph satisfaction

An artifact's M2A state describes *that artifact*. Graph satisfaction describes a
*topology*. Adding a sibling node must leave every existing artifact `valid`; only a change
to a node's own required dependency set may require its re-review, and that is reported as
a graph finding, never by mutating an M2A state.

Python never learns what a "design" is. It compares declared paths and declared edges
against recorded ones.
"""
from __future__ import annotations

import contextlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
sys.path.insert(0, str(ROOT / "scripts"))

from _artifact_identity import ARTIFACT_IDENTITY_FORMAT, artifact_identity  # noqa: E402
from _change_graph import GRAPH_FORMAT  # noqa: E402
from pb_ledger import LEDGER_FORMAT  # noqa: E402

PROPOSAL = "# Proposal\n\nProblem, scope, non-goals.\n"
DESIGN = "# Design\n\nApproach and alternatives.\n"
SPEC = "# Specification\n\nObservable behavior.\n"
CH = "specs/CH-001"


def review(purpose="proposal-reflection", role="spec-reflector"):
    return {"purpose": purpose, "role": role, "gate": "phases/spec/g.json", "gate_sha256": "a" * 64}


def entry(content, depends_on=None, rev=None):
    return {"content_sha256": artifact_identity(content.encode("utf-8")),
            "depends_on": depends_on or {}, "review": rev or review()}


def ledger(artifacts):
    return {"format": LEDGER_FORMAT, "artifact_identity": ARTIFACT_IDENTITY_FORMAT,
            "artifacts": artifacts}


def graph(artifacts, fmt=GRAPH_FORMAT):
    return {"format": fmt, "artifacts": artifacts}


class GraphFixture(unittest.TestCase):
    maxDiff = None

    def build(self, stack, files, graph_doc, ledger_doc, *, graph_dir=CH):
        root = Path(stack.enter_context(tempfile.TemporaryDirectory()))
        project = root / "project"
        project.mkdir()
        for rel, text in (files or {}).items():
            p = project / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8")
        gdir = project / graph_dir
        gdir.mkdir(parents=True, exist_ok=True)
        gpath = gdir / "graph.json"
        gpath.write_text(json.dumps(graph_doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        lpath = gdir / "ledger.json"
        lpath.write_text(json.dumps(ledger_doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return project, gpath, lpath

    def validate(self, project, gpath, lpath, run_root=None):
        cmd = [PYTHON, str(ROOT / "scripts" / "pb_graph.py"), "validate",
               "--graph", str(gpath), "--ledger", str(lpath), "--project-root", str(project)]
        if run_root is not None:
            cmd += ["--run-root", str(run_root)]
        cp = subprocess.run(cmd, text=True, capture_output=True, check=False)
        data = json.loads(cp.stdout) if cp.stdout.strip().startswith("{") else {}
        return cp, data

    def codes(self, data):
        return sorted(f["code"] for f in data.get("findings", []))


# ---------------------------------------------------------------- schema


class GraphSchemaTest(GraphFixture):
    """v1 semantics are explicit from day one. Malformed input fails hard, never quietly."""

    def test_format_tag_is_pinned(self):
        self.assertEqual(GRAPH_FORMAT, "proofbound-change-graph-v1")

    def test_a_well_formed_satisfied_graph_validates(self):
        with contextlib.ExitStack() as stack:
            project, g, l = self.build(
                stack, {f"{CH}/proposal.md": PROPOSAL},
                graph({f"{CH}/proposal.md": []}),
                ledger({f"{CH}/proposal.md": entry(PROPOSAL)}))
            cp, data = self.validate(project, g, l)
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            self.assertEqual(data["findings"], [])

    def test_unknown_graph_format_fails_closed(self):
        with contextlib.ExitStack() as stack:
            project, g, l = self.build(
                stack, {f"{CH}/proposal.md": PROPOSAL},
                graph({f"{CH}/proposal.md": []}, fmt="proofbound-change-graph-v2"),
                ledger({f"{CH}/proposal.md": entry(PROPOSAL)}))
            cp, _ = self.validate(project, g, l)
            self.assertEqual(cp.returncode, 2)
            self.assertIn("proofbound-change-graph-v2", cp.stderr)

    def test_missing_or_malformed_required_fields_fail_closed(self):
        bad = [
            {"artifacts": {}},                                     # no format
            {"format": GRAPH_FORMAT},                              # no artifacts
            {"format": GRAPH_FORMAT, "artifacts": []},             # artifacts not a map
            {"format": GRAPH_FORMAT, "artifacts": {f"{CH}/a.md": "x"}},   # deps not a list
            {"format": GRAPH_FORMAT, "artifacts": {f"{CH}/a.md": [1]}},   # dep not a string
        ]
        for doc in bad:
            with contextlib.ExitStack() as stack:
                project, g, l = self.build(stack, {}, doc, ledger({}))
                cp, _ = self.validate(project, g, l)
                self.assertEqual(cp.returncode, 2, doc)

    def test_unknown_fields_are_rejected_not_ignored(self):
        """v1 is strict: a field this version does not understand may carry meaning."""
        with contextlib.ExitStack() as stack:
            doc = graph({f"{CH}/proposal.md": []})
            doc["profile"] = "standard"
            project, g, l = self.build(stack, {f"{CH}/proposal.md": PROPOSAL}, doc,
                                       ledger({f"{CH}/proposal.md": entry(PROPOSAL)}))
            cp, _ = self.validate(project, g, l)
            self.assertEqual(cp.returncode, 2)
            self.assertIn("profile", cp.stderr)

    def test_duplicate_dependency_entries_are_rejected(self):
        with contextlib.ExitStack() as stack:
            project, g, l = self.build(
                stack, {f"{CH}/a.md": PROPOSAL, f"{CH}/b.md": DESIGN},
                graph({f"{CH}/a.md": [], f"{CH}/b.md": [f"{CH}/a.md", f"{CH}/a.md"]}),
                ledger({}))
            cp, _ = self.validate(project, g, l)
            self.assertEqual(cp.returncode, 2)
            self.assertIn("duplicate", cp.stderr.lower())

    def test_malformed_json_fails_closed(self):
        with contextlib.ExitStack() as stack:
            project, g, l = self.build(stack, {}, graph({}), ledger({}))
            g.write_text("{not json", encoding="utf-8")
            cp, _ = self.validate(project, g, l)
            self.assertEqual(cp.returncode, 2)

    def test_a_graph_may_not_declare_its_own_control_files(self):
        """A graph requiring itself is nonsense and would be permanently unsatisfiable."""
        for control in ("graph.json", "ledger.json"):
            with contextlib.ExitStack() as stack:
                project, g, l = self.build(stack, {}, graph({f"{CH}/{control}": []}), ledger({}))
                cp, _ = self.validate(project, g, l)
                self.assertEqual(cp.returncode, 2, control)
                self.assertIn("control file", cp.stderr.lower())


# ---------------------------------------------------------------- paths


class GraphPathTest(GraphFixture):
    """One repository-relative POSIX spelling per artifact. Alternates are rejected."""

    def test_unsafe_and_alternate_path_spellings_are_rejected_not_normalized(self):
        for bad in (f"./{CH}/a.md", f"{CH}/../CH-001/a.md", "specs\\CH-001\\a.md",
                    "/absolute/path/a.md", "../outside.md", ""):
            with contextlib.ExitStack() as stack:
                project, g, l = self.build(stack, {}, graph({bad: []}), ledger({}))
                cp, _ = self.validate(project, g, l)
                self.assertEqual(cp.returncode, 2, f"accepted unsafe path {bad!r}")

    def test_unsafe_dependency_paths_are_rejected(self):
        with contextlib.ExitStack() as stack:
            project, g, l = self.build(
                stack, {}, graph({f"{CH}/a.md": ["../outside.md"]}), ledger({}))
            cp, _ = self.validate(project, g, l)
            self.assertEqual(cp.returncode, 2)

    def test_case_colliding_members_are_rejected(self):
        """On a case-insensitive filesystem these name one file; the graph would be ambiguous."""
        with contextlib.ExitStack() as stack:
            project, g, l = self.build(
                stack, {}, graph({f"{CH}/a.md": [], f"{CH}/A.md": []}), ledger({}))
            cp, _ = self.validate(project, g, l)
            self.assertEqual(cp.returncode, 2)
            self.assertIn("case", cp.stderr.lower())

    def test_members_must_lie_within_the_graphs_own_directory(self):
        with contextlib.ExitStack() as stack:
            project, g, l = self.build(
                stack, {}, graph({"specs/CH-002/a.md": []}), ledger({}))
            cp, _ = self.validate(project, g, l)
            self.assertEqual(cp.returncode, 2)
            self.assertIn("scope", cp.stderr.lower())


# ---------------------------------------------------------------- topology


class GraphTopologyTest(GraphFixture):
    def test_an_empty_graph_is_legal_and_trivially_satisfied(self):
        with contextlib.ExitStack() as stack:
            project, g, l = self.build(stack, {}, graph({}), ledger({}))
            cp, data = self.validate(project, g, l)
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            self.assertEqual(data["findings"], [])

    def test_a_cycle_fails_closed(self):
        with contextlib.ExitStack() as stack:
            project, g, l = self.build(
                stack, {}, graph({f"{CH}/a.md": [f"{CH}/b.md"], f"{CH}/b.md": [f"{CH}/a.md"]}),
                ledger({}))
            cp, _ = self.validate(project, g, l)
            self.assertEqual(cp.returncode, 2)
            self.assertIn("cycle", cp.stderr.lower())

    def test_a_self_cycle_fails_closed(self):
        """Reported by the more precise self-dependency check, not the generic detector.

        A self-loop is a cycle, but naming it exactly is more useful than "cycle a -> a",
        and both fail closed with the same exit code, which is what callers depend on.
        """
        with contextlib.ExitStack() as stack:
            project, g, l = self.build(
                stack, {}, graph({f"{CH}/a.md": [f"{CH}/a.md"]}), ledger({}))
            cp, _ = self.validate(project, g, l)
            self.assertEqual(cp.returncode, 2)
            self.assertIn("depend on itself", cp.stderr.lower())

    def test_findings_are_deterministically_ordered(self):
        with contextlib.ExitStack() as stack:
            project, g, l = self.build(
                stack, {},
                graph({f"{CH}/a.md": [], f"{CH}/b.md": [f"{CH}/a.md"], f"{CH}/c.md": [f"{CH}/a.md"]}),
                ledger({}))
            first = self.validate(project, g, l)[1]["findings"]
            for _ in range(3):
                self.assertEqual(self.validate(project, g, l)[1]["findings"], first)


# ---------------------------------------------------------------- exactness


class GraphExactnessTest(GraphFixture):
    def test_a_declared_member_with_no_accepted_record_is_reported(self):
        with contextlib.ExitStack() as stack:
            project, g, l = self.build(
                stack, {f"{CH}/a.md": PROPOSAL}, graph({f"{CH}/a.md": []}), ledger({}))
            cp, data = self.validate(project, g, l)
            self.assertEqual(cp.returncode, 1)
            self.assertEqual(self.codes(data), ["missing-accepted-record"])

    def test_ordinary_files_in_the_directory_are_not_graph_members(self):
        """Filesystem presence is not authority (P11). Only declaration and acceptance are."""
        with contextlib.ExitStack() as stack:
            project, g, l = self.build(
                stack,
                {f"{CH}/a.md": PROPOSAL, f"{CH}/notes.md": "scratch\n",
                 f"{CH}/research.txt": "links\n", f"{CH}/screenshots/x.md": "img\n"},
                graph({f"{CH}/a.md": []}), ledger({f"{CH}/a.md": entry(PROPOSAL)}))
            cp, data = self.validate(project, g, l)
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            self.assertEqual(data["findings"], [])

    def test_an_accepted_record_in_scope_that_the_graph_does_not_declare_is_reported(self):
        with contextlib.ExitStack() as stack:
            project, g, l = self.build(
                stack, {f"{CH}/a.md": PROPOSAL, f"{CH}/d.md": DESIGN},
                graph({f"{CH}/a.md": []}),
                ledger({f"{CH}/a.md": entry(PROPOSAL), f"{CH}/d.md": entry(DESIGN)}))
            cp, data = self.validate(project, g, l)
            self.assertEqual(cp.returncode, 1)
            self.assertEqual(self.codes(data), ["undeclared-member"])

    def test_scope_uses_path_semantics_not_string_prefix(self):
        """`specs/CH-0012/` must not fall inside `specs/CH-001/`."""
        with contextlib.ExitStack() as stack:
            project, g, l = self.build(
                stack, {f"{CH}/a.md": PROPOSAL, "specs/CH-0012/x.md": DESIGN},
                graph({f"{CH}/a.md": []}),
                ledger({f"{CH}/a.md": entry(PROPOSAL), "specs/CH-0012/x.md": entry(DESIGN)}))
            cp, data = self.validate(project, g, l)
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            self.assertEqual(data["findings"], [])

    def test_a_nested_record_inside_scope_still_counts(self):
        with contextlib.ExitStack() as stack:
            project, g, l = self.build(
                stack, {f"{CH}/a.md": PROPOSAL, f"{CH}/nested/x.md": DESIGN},
                graph({f"{CH}/a.md": []}),
                ledger({f"{CH}/a.md": entry(PROPOSAL), f"{CH}/nested/x.md": entry(DESIGN)}))
            cp, data = self.validate(project, g, l)
            self.assertEqual(self.codes(data), ["undeclared-member"])

    def test_control_files_never_count_toward_exactness(self):
        with contextlib.ExitStack() as stack:
            project, g, l = self.build(
                stack, {f"{CH}/a.md": PROPOSAL},
                graph({f"{CH}/a.md": []}),
                ledger({f"{CH}/a.md": entry(PROPOSAL),
                        f"{CH}/ledger.json": entry("{}\n"),
                        f"{CH}/graph.json": entry("{}\n")}))
            cp, data = self.validate(project, g, l)
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            self.assertEqual(data["findings"], [])


# ---------------------------------------------------------------- edges


class GraphEdgeTest(GraphFixture):
    def three_nodes(self):
        return {f"{CH}/a.md": [], f"{CH}/b.md": [f"{CH}/a.md"],
                f"{CH}/c.md": [f"{CH}/a.md", f"{CH}/b.md"]}

    def accepted_three(self):
        a = artifact_identity(PROPOSAL.encode())
        b = artifact_identity(DESIGN.encode())
        return {f"{CH}/a.md": entry(PROPOSAL),
                f"{CH}/b.md": entry(DESIGN, {f"{CH}/a.md": a}, review("design-reflection")),
                f"{CH}/c.md": entry(SPEC, {f"{CH}/a.md": a, f"{CH}/b.md": b},
                                    review("specification-reflection"))}

    def files(self):
        return {f"{CH}/a.md": PROPOSAL, f"{CH}/b.md": DESIGN, f"{CH}/c.md": SPEC}

    def test_a_fully_accepted_three_node_dag_is_satisfied(self):
        with contextlib.ExitStack() as stack:
            project, g, l = self.build(stack, self.files(), graph(self.three_nodes()),
                                       ledger(self.accepted_three()))
            cp, data = self.validate(project, g, l)
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            self.assertEqual(data["findings"], [])

    def test_a_required_edge_the_record_lacks_is_reported(self):
        with contextlib.ExitStack() as stack:
            accepted = self.accepted_three()
            accepted[f"{CH}/c.md"]["depends_on"].pop(f"{CH}/b.md")
            project, g, l = self.build(stack, self.files(), graph(self.three_nodes()),
                                       ledger(accepted))
            cp, data = self.validate(project, g, l)
            self.assertEqual(cp.returncode, 1)
            self.assertEqual(self.codes(data), ["missing-required-edge"])

    def test_a_recorded_edge_the_graph_does_not_declare_is_reported(self):
        """Exact edges: topology may not expand past what authority declared (P7)."""
        with contextlib.ExitStack() as stack:
            topology = self.three_nodes()
            topology[f"{CH}/c.md"] = [f"{CH}/a.md"]          # graph no longer requires c -> b
            project, g, l = self.build(stack, self.files(), graph(topology),
                                       ledger(self.accepted_three()))
            cp, data = self.validate(project, g, l)
            self.assertEqual(cp.returncode, 1)
            self.assertEqual(self.codes(data), ["undeclared-edge"])

    def test_edge_comparison_is_skipped_for_a_member_with_no_record(self):
        """One clear finding beats a cascade about edges of an artifact that does not exist."""
        with contextlib.ExitStack() as stack:
            accepted = self.accepted_three()
            accepted.pop(f"{CH}/c.md")
            project, g, l = self.build(stack, self.files(), graph(self.three_nodes()),
                                       ledger(accepted))
            cp, data = self.validate(project, g, l)
            self.assertEqual(self.codes(data), ["missing-accepted-record"])

    def test_a_dependency_on_an_accepted_artifact_outside_the_graph_is_legal(self):
        """Membership and dependency target are different relations."""
        external = "docs/architecture/x.md"
        with contextlib.ExitStack() as stack:
            ext_id = artifact_identity(SPEC.encode())
            project, g, l = self.build(
                stack, {f"{CH}/a.md": PROPOSAL, external: SPEC},
                graph({f"{CH}/a.md": [external]}),
                ledger({external: entry(SPEC),
                        f"{CH}/a.md": entry(PROPOSAL, {external: ext_id})}))
            cp, data = self.validate(project, g, l)
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            self.assertEqual(data["findings"], [])

    def test_a_dependency_target_with_no_accepted_record_is_reported(self):
        """A path existing is not an accepted identity to depend on."""
        with contextlib.ExitStack() as stack:
            project, g, l = self.build(
                stack, {f"{CH}/a.md": PROPOSAL, "README.md": "readme\n"},
                graph({f"{CH}/a.md": ["README.md"]}),
                ledger({f"{CH}/a.md": entry(PROPOSAL)}))
            cp, data = self.validate(project, g, l)
            self.assertEqual(cp.returncode, 1)
            self.assertIn("unresolved-dependency-target", self.codes(data))


# ---------------------------------------------------------------- the M2A boundary


class GraphDoesNotDisturbArtifactValidityTest(GraphFixture):
    """The core M2B proof. Topology is not staleness."""

    def base(self):
        a = artifact_identity(PROPOSAL.encode())
        return ({f"{CH}/a.md": PROPOSAL, f"{CH}/b.md": DESIGN},
                {f"{CH}/a.md": [], f"{CH}/b.md": [f"{CH}/a.md"]},
                {f"{CH}/a.md": entry(PROPOSAL),
                 f"{CH}/b.md": entry(DESIGN, {f"{CH}/a.md": a}, review("design-reflection"))})

    def states(self, data):
        return {a["path"]: a["state"] for a in data["artifacts"]}

    def test_G1_is_satisfied(self):
        files, topology, accepted = self.base()
        with contextlib.ExitStack() as stack:
            project, g, l = self.build(stack, files, graph(topology), ledger(accepted))
            cp, data = self.validate(project, g, l)
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            self.assertEqual(self.states(data), {f"{CH}/a.md": "valid", f"{CH}/b.md": "valid"})

    def test_G2_adding_a_sibling_leaves_every_artifact_valid(self):
        """Topology grew; no artifact's reviewed context changed. Nothing may go stale."""
        files, topology, accepted = self.base()
        topology[f"{CH}/c.md"] = [f"{CH}/a.md"]
        with contextlib.ExitStack() as stack:
            project, g, l = self.build(stack, files, graph(topology), ledger(accepted))
            cp, data = self.validate(project, g, l)
            self.assertEqual(cp.returncode, 1)
            self.assertEqual(self.codes(data), ["missing-accepted-record"])
            self.assertEqual(self.states(data), {f"{CH}/a.md": "valid", f"{CH}/b.md": "valid"},
                             "a sibling addition must not make any artifact stale")

    def test_G3_adding_an_edge_reports_topology_without_rewriting_validity(self):
        """B's bytes never moved, so B stays `valid` — but the graph is unsatisfied."""
        files, topology, accepted = self.base()
        c_id = artifact_identity(SPEC.encode())
        files[f"{CH}/c.md"] = SPEC
        topology[f"{CH}/c.md"] = [f"{CH}/a.md"]
        topology[f"{CH}/b.md"] = [f"{CH}/a.md", f"{CH}/c.md"]
        a_id = artifact_identity(PROPOSAL.encode())
        accepted[f"{CH}/c.md"] = entry(SPEC, {f"{CH}/a.md": a_id}, review("design-reflection"))
        with contextlib.ExitStack() as stack:
            project, g, l = self.build(stack, files, graph(topology), ledger(accepted))
            cp, data = self.validate(project, g, l)
            self.assertEqual(cp.returncode, 1)
            self.assertEqual(self.codes(data), ["missing-required-edge"])
            self.assertEqual(self.states(data),
                             {f"{CH}/a.md": "valid", f"{CH}/b.md": "valid", f"{CH}/c.md": "valid"},
                             "an edge addition must not rewrite artifact content validity")
            finding = data["findings"][0]
            self.assertEqual(finding["artifact"], f"{CH}/b.md")
            self.assertIn(f"{CH}/c.md", finding["related"])

    def test_content_drift_still_produces_ordinary_M2A_states(self):
        files, topology, accepted = self.base()
        with contextlib.ExitStack() as stack:
            project, g, l = self.build(stack, files, graph(topology), ledger(accepted))
            (project / CH / "a.md").write_text(PROPOSAL + "edited\n", encoding="utf-8")
            cp, data = self.validate(project, g, l)
            self.assertEqual(cp.returncode, 1)
            self.assertEqual(self.states(data),
                             {f"{CH}/a.md": "invalid", f"{CH}/b.md": "needs-revalidation"})
            self.assertEqual(self.codes(data), ["artifact-not-valid", "artifact-not-valid"])


# ---------------------------------------------------------------- identity


class GraphIdentityTest(GraphFixture):
    """Graph identity reuses the artifact text protocol; no second hashing protocol."""

    def test_graph_identity_is_the_artifact_text_identity_of_the_file(self):
        from _artifact_identity import artifact_identity_file
        with contextlib.ExitStack() as stack:
            project, g, l = self.build(stack, {}, graph({}), ledger({}))
            self.assertEqual(artifact_identity_file(g), artifact_identity(g.read_bytes()))

    def test_a_crlf_checkout_does_not_move_graph_identity(self):
        from _artifact_identity import artifact_identity_file
        with contextlib.ExitStack() as stack:
            project, g, l = self.build(stack, {}, graph({f"{CH}/a.md": []}), ledger({}))
            lf = artifact_identity_file(g)
            g.write_bytes(g.read_bytes().replace(b"\n", b"\r\n"))
            self.assertEqual(artifact_identity_file(g), lf)

    def test_whitespace_edits_do_change_graph_identity(self):
        """Text identity, deliberately: any textual edit is a new graph."""
        from _artifact_identity import artifact_identity_file
        with contextlib.ExitStack() as stack:
            project, g, l = self.build(stack, {}, graph({f"{CH}/a.md": []}), ledger({}))
            before = artifact_identity_file(g)
            g.write_text(g.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            self.assertNotEqual(artifact_identity_file(g), before)


if __name__ == "__main__":
    unittest.main()
