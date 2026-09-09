from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
import hashlib
import html
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile
from typing import Protocol

from .landing_contracts import (
    LandingContractError,
    StaticLandingSpecV1,
    landing_digest,
    same_origin_root_path,
)


TARGET_REPOSITORY_ID = "github.com/Dimkox/ai-dark-factory-landing"
TARGET_BASE_SHA = "699010380f4f90a0193a9c22090c35e6aded7d2c"
TARGET_BASE_TREE = "f7dbbd80c6e95d2a365109d937f5be76d8fe0bd4"
TARGET_DEFAULT_BRANCH = "main"
LANDING_WRITE_PATHS = frozenset({"index.html", "content.css"})
MAX_LANDING_FILE_BYTES = 2 * 1_048_576
RENDERER_VERSION = "1.0.1"
FIXED_COMMIT_TIME = "2000-01-01T00:00:00Z"
FIXED_COMMIT_NAME = "Adaptive Landing Renderer"
FIXED_COMMIT_EMAIL = "landing-renderer@invalid.local"
_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_REPAIR_CODE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_REPAIR_CODES = frozenset({"copy_density", "missing_required_section"})


class LandingRenderError(RuntimeError):
    pass


@dataclass(frozen=True)
class GitTreeMember:
    path: str
    mode: str
    object_id: str


@dataclass(frozen=True)
class LandingSourceSurfaceFacts:
    robots_tag: str
    canonical_tag: str
    alternate_tags: tuple[str, ...]
    index_stylesheet_sha256: str
    jsonld_sha256: str


@dataclass(frozen=True)
class RenderedLandingFiles:
    index_html: bytes
    content_css: bytes
    renderer_digest: str


@dataclass(frozen=True)
class LandingCandidateSnapshot:
    repository_id: str
    source_sha: str
    source_tree: str
    candidate_sha: str
    candidate_tree: str
    ordinal: int
    changed_paths: tuple[str, ...]
    source_members: tuple[GitTreeMember, ...]
    candidate_members: tuple[GitTreeMember, ...]
    source_index_html: bytes
    source_content_css: bytes
    index_html: bytes
    content_css: bytes
    renderer_digest: str
    workspace_result_digest: str
    workspace_mode: int
    clone_strategy: str
    head_detached: bool
    object_storage_independent: bool
    commit_time: str


class LandingRenderer(Protocol):
    def render(
        self,
        source_index_html: bytes,
        source_content_css: bytes,
        spec: StaticLandingSpecV1,
        *,
        repair_codes: tuple[str, ...],
    ) -> RenderedLandingFiles: ...


def source_surface_facts(html_text: str) -> LandingSourceSurfaceFacts:
    if not isinstance(html_text, str):
        raise LandingRenderError("source_html")

    def exactly_one(pattern: str, code: str, *, flags: int = 0) -> str:
        matches = re.findall(pattern, html_text, flags)
        if len(matches) != 1:
            raise LandingRenderError(code)
        return matches[0]

    robots = exactly_one(
        r'<meta\s+name="robots"\s+content="[^"]+">', "source_robots"
    )
    if "index, follow" not in robots:
        raise LandingRenderError("source_robots")
    canonical = exactly_one(
        r'<link\s+rel="canonical"\s+href="https://therealaidarkfactory\.online/">',
        "source_canonical",
    )
    alternates = tuple(
        re.findall(r'<link\s+rel="alternate"\s+hreflang="[^"]+"\s+href="[^"]+">', html_text)
    )
    if len(alternates) != 7 or len(set(alternates)) != len(alternates):
        raise LandingRenderError("source_hreflang")
    link_tags = re.findall(r"<link\b[^>]*>", html_text, re.IGNORECASE)
    stylesheet_tags = tuple(
        tag
        for tag in link_tags
        if "stylesheet" in tag.lower()
    )
    index_stylesheet = '<link rel="stylesheet" href="/index.css">'
    content_stylesheet = '<link rel="stylesheet" href="/content.css">'
    if (
        stylesheet_tags.count(index_stylesheet) != 1
        or stylesheet_tags.count(content_stylesheet) > 1
        or any(
            tag not in {index_stylesheet, content_stylesheet}
            for tag in stylesheet_tags
        )
    ):
        raise LandingRenderError("source_active_content")
    scripts = re.findall(r"<script(?:\s[^>]*)?>.*?</script>", html_text, re.DOTALL)
    lowered = html_text.lower()
    if (
        re.search(r"<style\b", lowered)
        or re.search(r"\sstyle\s*=", lowered)
        or len(scripts) != 1
    ):
        raise LandingRenderError("source_active_content")
    if not scripts[0].startswith('<script type="application/ld+json">'):
        raise LandingRenderError("source_active_content")
    if "<form" in lowered or "google-analytics" in lowered or "gtag(" in lowered:
        raise LandingRenderError("source_active_content")
    return LandingSourceSurfaceFacts(
        robots,
        canonical,
        alternates,
        hashlib.sha256(index_stylesheet.encode("utf-8")).hexdigest(),
        hashlib.sha256(scripts[0].encode("utf-8")).hexdigest(),
    )


class DeterministicLandingRenderer:
    def render(
        self,
        source_index_html: bytes,
        source_content_css: bytes,
        spec: StaticLandingSpecV1,
        *,
        repair_codes: tuple[str, ...],
    ) -> RenderedLandingFiles:
        if not isinstance(spec, StaticLandingSpecV1):
            raise LandingRenderError("spec_type")
        if spec.robots_policy != "preserve_source":
            raise LandingRenderError("robots_policy")
        repairs = _validated_repairs(repair_codes)
        source_html = _decode_file(source_index_html, "source_index")
        source_css = _decode_file(source_content_css, "source_css")
        facts = source_surface_facts(source_html)
        if "@import" in source_css.lower() or "url(http" in source_css.lower():
            raise LandingRenderError("source_remote_dependency")

        marker = '<main id="content">'
        start = source_html.find(marker)
        end_start = source_html.find("</main>", start + len(marker))
        if start < 0 or end_start < 0 or source_html.find(marker, start + 1) >= 0:
            raise LandingRenderError("source_main_boundary")
        end = end_start + len("</main>")
        prefix = source_html[:start]
        suffix = source_html[end:]
        stylesheet = '  <link rel="stylesheet" href="/content.css">\n'
        if stylesheet not in prefix:
            head_end = prefix.find("</head>")
            if head_end < 0:
                raise LandingRenderError("source_head_boundary")
            prefix = prefix[:head_end] + stylesheet + prefix[head_end:]
        rendered_main = _render_main(spec, repairs)
        rendered_html = prefix + rendered_main + suffix
        rendered_css = source_css.rstrip("\n") + "\n\n" + _render_css(spec, repairs)
        if source_surface_facts(rendered_html) != facts:
            raise LandingRenderError("source_fact_drift")
        _validate_generated_surface(rendered_html, rendered_css)
        index_bytes = rendered_html.encode("utf-8")
        css_bytes = rendered_css.encode("utf-8")
        if max(len(index_bytes), len(css_bytes)) > MAX_LANDING_FILE_BYTES:
            raise LandingRenderError("render_size")
        values = {
            "renderer_version": RENDERER_VERSION,
            "spec_digest": spec.spec_digest,
            "repair_codes": list(repairs),
            "source_index_sha256": hashlib.sha256(source_index_html).hexdigest(),
            "source_css_sha256": hashlib.sha256(source_content_css).hexdigest(),
            "index_sha256": hashlib.sha256(index_bytes).hexdigest(),
            "css_sha256": hashlib.sha256(css_bytes).hexdigest(),
        }
        return RenderedLandingFiles(
            index_bytes,
            css_bytes,
            landing_digest("renderer", values),
        )


def _validated_repairs(repair_codes: Sequence[str]) -> tuple[str, ...]:
    if not isinstance(repair_codes, (tuple, list)):
        raise LandingRenderError("repair_codes")
    values = tuple(repair_codes)
    if (
        values != tuple(sorted(set(values)))
        or any(
            not isinstance(value, str)
            or not _REPAIR_CODE.fullmatch(value)
            or value not in _REPAIR_CODES
            for value in values
        )
    ):
        raise LandingRenderError("repair_codes")
    return values


def _decode_file(value: bytes, code: str) -> str:
    if not isinstance(value, bytes) or not value or len(value) > MAX_LANDING_FILE_BYTES:
        raise LandingRenderError(code)
    try:
        text = value.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise LandingRenderError(code) from exc
    if "\r" in text or "\x00" in text:
        raise LandingRenderError(code)
    return text


def _render_main(spec: StaticLandingSpecV1, repairs: tuple[str, ...]) -> str:
    attributes = (
        f'data-spec-digest="{spec.spec_digest}" '
        f'data-repairs="{html.escape(",".join(repairs), quote=True)}"'
    )
    lines = [
        f'  <main id="content" class="l5-generated" {attributes}>',
        '    <span id="product" class="l5-anchor" aria-hidden="true"></span>',
        '    <span id="automation" class="l5-anchor" aria-hidden="true"></span>',
        '    <section class="l5-hero" aria-labelledby="l5-title">',
        f'      <p class="l5-kicker">{html.escape(spec.site_id)}</p>',
        f'      <h1 id="l5-title">{html.escape(spec.title)}</h1>',
        f'      <p class="l5-lead">{html.escape(spec.description)}</p>',
        "    </section>",
    ]
    for index, section in enumerate(spec.sections, 1):
        try:
            cta_path = same_origin_root_path(section.cta_path)
        except LandingContractError as exc:
            raise LandingRenderError("cta_path") from exc
        lines.extend(
            [
                f'    <section class="l5-section" id="section-{index}">',
                f"      <h2>{html.escape(section.heading)}</h2>",
            ]
        )
        if section.body:
            lines.append(f"      <p>{html.escape(section.body)}</p>")
        if section.items:
            lines.append("      <ul>")
            lines.extend(f"        <li>{html.escape(item)}</li>" for item in section.items)
            lines.append("      </ul>")
        if section.cta_label:
            lines.append(
                f'      <a class="l5-action" href="{html.escape(cta_path, quote=True)}">'
                f"{html.escape(section.cta_label)}</a>"
            )
        lines.append("    </section>")
    lines.extend(("  </main>", ""))
    return "\n".join(lines)


def _render_css(spec: StaticLandingSpecV1, repairs: tuple[str, ...]) -> str:
    compact = "0.9rem" if "copy_density" in repairs else "1rem"
    return "\n".join(
        (
            f"/* adaptive-landing-renderer/{RENDERER_VERSION} spec:{spec.spec_digest} */",
            ".l5-generated { width: min(calc(100% - 40px), 1120px); margin-inline: auto; }",
            ".l5-anchor { display: block; position: relative; top: -80px; visibility: hidden; }",
            ".l5-hero { padding: clamp(72px, 11vw, 136px) 0 64px; }",
            ".l5-kicker { color: var(--cyan); font-family: var(--mono); }",
            ".l5-generated h1 { max-width: 900px; margin: 0; font-size: clamp(48px, 8vw, 92px); }",
            f".l5-lead, .l5-section p, .l5-section li {{ font-size: {compact}; }}",
            ".l5-lead { max-width: 760px; color: var(--muted); }",
            ".l5-section { padding: 56px 0; border-top: 1px solid var(--line); }",
            ".l5-action { display: inline-flex; margin-top: 18px; color: var(--amber); }",
            "",
        )
    )


def _validate_generated_surface(html_text: str, css_text: str) -> None:
    lowered = html_text.lower()
    scripts = re.findall(r"<script(?:\s[^>]*)?>.*?</script>", html_text, re.DOTALL)
    if len(scripts) != 1 or not scripts[0].startswith(
        '<script type="application/ld+json">'
    ):
        raise LandingRenderError("active_content")
    for forbidden in ("<form", "google-analytics", "gtag(", "javascript:"):
        if forbidden in lowered:
            raise LandingRenderError("active_content")
    css_lowered = css_text.lower()
    if "@import" in css_lowered or "url(http" in css_lowered or "javascript:" in css_lowered:
        raise LandingRenderError("remote_dependency")


class ExactGitLandingWorkspace:
    def __init__(
        self,
        source_repository: Path,
        *,
        scratch_root: Path | None = None,
        workspace_observer: Callable[[Path], None] | None = None,
    ) -> None:
        source = Path(source_repository)
        if not source.is_absolute():
            raise LandingRenderError("source_path")
        self._source = source.resolve()
        self._scratch_root = Path(scratch_root).resolve() if scratch_root else None
        self._observer = workspace_observer
        git = shutil.which("git")
        upload_pack = shutil.which("git-upload-pack")
        if not git or not upload_pack:
            raise LandingRenderError("git_unavailable")
        self._git_executable = str(Path(git).resolve())
        self._upload_pack = str(Path(upload_pack).absolute())

    def build_candidate(
        self,
        spec: StaticLandingSpecV1,
        renderer: LandingRenderer,
        *,
        ordinal: int,
        repair_codes: tuple[str, ...] = (),
    ) -> LandingCandidateSnapshot:
        if type(ordinal) is not int or not 1 <= ordinal <= 3:
            raise LandingRenderError("attempt_ordinal")
        repairs = _validated_repairs(repair_codes)
        if (ordinal == 1 and repairs) or (ordinal > 1 and not repairs):
            raise LandingRenderError("repair_binding")
        source_guard = self._source_guard()
        workspace_root: Path | None = None
        failure: BaseException | None = None
        try:
            workspace_root = self._private_directory()
            repository = workspace_root / "candidate"
            environment = self._environment(workspace_root)
            self._clone(repository, environment)
            self._checkout_exact(repository, environment)
            if self._observer is not None:
                self._observer(workspace_root)
            source_members = self._tree_members(repository, TARGET_BASE_SHA, environment)
            source_index = _read_regular(repository / "index.html")
            source_css = _read_regular(repository / "content.css")
            rendered = renderer.render(
                source_index,
                source_css,
                spec,
                repair_codes=repairs,
            )
            _write_regular(repository / "index.html", rendered.index_html)
            _write_regular(repository / "content.css", rendered.content_css)
            candidate_sha, candidate_tree = self._seal_commit(repository, environment)
            candidate_members = self._tree_members(repository, candidate_sha, environment)
            changed_paths = self._changed_paths(
                repository, TARGET_BASE_SHA, candidate_sha, environment
            )
            self._validate_candidate(source_members, candidate_members, changed_paths)
            independent = self._independent_objects(repository)
            if not independent:
                raise LandingRenderError("hardlinked_objects")
            values = {
                "repository_id": TARGET_REPOSITORY_ID,
                "source_sha": TARGET_BASE_SHA,
                "source_tree": TARGET_BASE_TREE,
                "candidate_sha": candidate_sha,
                "candidate_tree": candidate_tree,
                "ordinal": ordinal,
                "changed_paths": list(changed_paths),
                "source_members": [member.__dict__ for member in source_members],
                "candidate_members": [member.__dict__ for member in candidate_members],
                "renderer_digest": rendered.renderer_digest,
                "clone_strategy": "no-local-no-hardlinks",
                "commit_time": FIXED_COMMIT_TIME,
            }
            return LandingCandidateSnapshot(
                TARGET_REPOSITORY_ID,
                TARGET_BASE_SHA,
                TARGET_BASE_TREE,
                candidate_sha,
                candidate_tree,
                ordinal,
                changed_paths,
                source_members,
                candidate_members,
                source_index,
                source_css,
                rendered.index_html,
                rendered.content_css,
                rendered.renderer_digest,
                landing_digest("workspace-result", values),
                stat.S_IMODE(workspace_root.stat().st_mode),
                "no-local-no-hardlinks",
                self._head_detached(repository),
                independent,
                FIXED_COMMIT_TIME,
            )
        except BaseException as exc:
            failure = exc
            raise
        finally:
            cleanup_error = None
            if workspace_root is not None:
                try:
                    shutil.rmtree(workspace_root)
                except OSError as exc:
                    cleanup_error = LandingRenderError("workspace_cleanup")
                    cleanup_error.__cause__ = exc
            guard_error = None
            try:
                if self._source_guard() != source_guard:
                    guard_error = LandingRenderError("source_mutation")
            except LandingRenderError as exc:
                guard_error = exc
            if failure is None and (cleanup_error is not None or guard_error is not None):
                raise cleanup_error or guard_error  # type: ignore[misc]

    def _source_guard(self) -> tuple[bytes, bytes, bytes]:
        if not self._source.is_dir() or not (self._source / ".git").is_dir():
            raise LandingRenderError("source_identity")
        environment = self._environment(self._source)
        head = self._git(("rev-parse", "HEAD"), cwd=self._source, env=environment).strip()
        tree = self._git(("rev-parse", "HEAD^{tree}"), cwd=self._source, env=environment).strip()
        if head != TARGET_BASE_SHA.encode() or tree != TARGET_BASE_TREE.encode():
            raise LandingRenderError("source_identity")
        refs = self._git(
            ("for-each-ref", "--format=%(refname)%00%(objectname)"),
            cwd=self._source,
            env=environment,
        )
        return head, tree, refs

    def _private_directory(self) -> Path:
        previous = os.umask(0o077)
        try:
            created = Path(
                tempfile.mkdtemp(
                    prefix="adaptive-landing-",
                    dir=str(self._scratch_root) if self._scratch_root else None,
                )
            )
        finally:
            os.umask(previous)
        created.chmod(0o700)
        return created

    def _environment(self, home: Path) -> dict[str, str]:
        return {
            "HOME": str(home),
            "PATH": "/usr/bin:/bin",
            "LC_ALL": "C",
            "TZ": "UTC",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_ASKPASS": "/bin/false",
            "SSH_ASKPASS": "/bin/false",
        }

    def _clone(self, repository: Path, environment: Mapping[str, str]) -> None:
        self._git(
            (
                "-c",
                "protocol.allow=never",
                "-c",
                "protocol.file.allow=always",
                "clone",
                "--no-local",
                "--no-hardlinks",
                "--no-tags",
                "--no-checkout",
                "--single-branch",
                f"--branch={TARGET_DEFAULT_BRANCH}",
                f"--upload-pack={self._upload_pack}",
                str(self._source),
                str(repository),
            ),
            cwd=repository.parent,
            env=environment,
        )

    def _checkout_exact(self, repository: Path, environment: Mapping[str, str]) -> None:
        self._git(
            ("-c", "advice.detachedHead=false", "checkout", "--detach", "--force", TARGET_BASE_SHA),
            cwd=repository,
            env=environment,
        )
        tree = self._git(
            ("rev-parse", "HEAD^{tree}"), cwd=repository, env=environment
        ).strip()
        if tree != TARGET_BASE_TREE.encode():
            raise LandingRenderError("checkout_identity")
        self._git(("remote", "remove", "origin"), cwd=repository, env=environment)

    def _seal_commit(
        self, repository: Path, environment: Mapping[str, str]
    ) -> tuple[str, str]:
        self._git(
            ("add", "--", "index.html", "content.css"),
            cwd=repository,
            env=environment,
        )
        staged = tuple(
            path
            for path in self._git(
                ("diff", "--cached", "--name-only", "-z"),
                cwd=repository,
                env=environment,
            )
            .decode("utf-8")
            .split("\x00")
            if path
        )
        if tuple(sorted(staged)) != tuple(sorted(LANDING_WRITE_PATHS)):
            raise LandingRenderError("write_scope")
        tree = self._git(("write-tree",), cwd=repository, env=environment).strip().decode()
        if not _HEX40.fullmatch(tree):
            raise LandingRenderError("candidate_tree")
        commit_environment = {
            **environment,
            "GIT_AUTHOR_NAME": FIXED_COMMIT_NAME,
            "GIT_AUTHOR_EMAIL": FIXED_COMMIT_EMAIL,
            "GIT_COMMITTER_NAME": FIXED_COMMIT_NAME,
            "GIT_COMMITTER_EMAIL": FIXED_COMMIT_EMAIL,
            "GIT_AUTHOR_DATE": FIXED_COMMIT_TIME,
            "GIT_COMMITTER_DATE": FIXED_COMMIT_TIME,
        }
        commit = self._git(
            ("-c", "commit.gpgSign=false", "commit-tree", tree, "-p", TARGET_BASE_SHA),
            cwd=repository,
            env=commit_environment,
            input_bytes=b"L5 landing candidate\n",
        ).strip().decode()
        if not _HEX40.fullmatch(commit):
            raise LandingRenderError("candidate_commit")
        return commit, tree

    def _tree_members(
        self, repository: Path, revision: str, environment: Mapping[str, str]
    ) -> tuple[GitTreeMember, ...]:
        raw = self._git(
            ("ls-tree", "-r", "-z", "--full-tree", revision),
            cwd=repository,
            env=environment,
        )
        members = []
        for entry in raw.split(b"\x00"):
            if not entry:
                continue
            try:
                metadata, path_raw = entry.split(b"\t", 1)
                mode, object_type, object_id = metadata.decode("ascii").split(" ")
                path = path_raw.decode("utf-8")
            except (ValueError, UnicodeDecodeError) as exc:
                raise LandingRenderError("tree_inventory") from exc
            if object_type != "blob" or not _HEX40.fullmatch(object_id):
                raise LandingRenderError("tree_inventory")
            members.append(GitTreeMember(path, mode, object_id))
        result = tuple(sorted(members, key=lambda item: item.path))
        if not result or len({item.path for item in result}) != len(result):
            raise LandingRenderError("tree_inventory")
        return result

    def _changed_paths(
        self,
        repository: Path,
        base: str,
        candidate: str,
        environment: Mapping[str, str],
    ) -> tuple[str, ...]:
        raw = self._git(
            ("diff-tree", "--no-commit-id", "--name-only", "-r", "-z", base, candidate),
            cwd=repository,
            env=environment,
        )
        try:
            return tuple(sorted(path for path in raw.decode("utf-8").split("\x00") if path))
        except UnicodeDecodeError as exc:
            raise LandingRenderError("changed_paths") from exc

    def _validate_candidate(
        self,
        source: tuple[GitTreeMember, ...],
        candidate: tuple[GitTreeMember, ...],
        changed_paths: tuple[str, ...],
    ) -> None:
        if set(changed_paths) != LANDING_WRITE_PATHS:
            raise LandingRenderError("write_scope")
        source_map = {item.path: (item.mode, item.object_id) for item in source}
        candidate_map = {item.path: (item.mode, item.object_id) for item in candidate}
        if set(source_map) != set(candidate_map):
            raise LandingRenderError("tree_shape")
        for path in source_map:
            if path not in LANDING_WRITE_PATHS and source_map[path] != candidate_map[path]:
                raise LandingRenderError("protected_tree_drift")
            if source_map[path][0] != candidate_map[path][0]:
                raise LandingRenderError("mode_drift")

    def _independent_objects(self, repository: Path) -> bool:
        candidate_objects = repository / ".git" / "objects"
        source_objects = self._source / ".git" / "objects"
        if (candidate_objects / "info" / "alternates").exists():
            return False

        def inodes(root: Path) -> set[tuple[int, int]]:
            result = set()
            for path in root.rglob("*"):
                try:
                    metadata = path.stat(follow_symlinks=False)
                except OSError:
                    continue
                if stat.S_ISREG(metadata.st_mode):
                    result.add((metadata.st_dev, metadata.st_ino))
            return result

        return not (inodes(candidate_objects) & inodes(source_objects))

    @staticmethod
    def _head_detached(repository: Path) -> bool:
        try:
            value = (repository / ".git" / "HEAD").read_text(encoding="ascii").strip()
        except (OSError, UnicodeDecodeError) as exc:
            raise LandingRenderError("detached_head") from exc
        return bool(_HEX40.fullmatch(value))

    def _git(
        self,
        arguments: tuple[str, ...],
        *,
        cwd: Path,
        env: Mapping[str, str],
        input_bytes: bytes | None = None,
    ) -> bytes:
        try:
            completed = subprocess.run(
                (self._git_executable, *arguments),
                cwd=cwd,
                env=dict(env),
                input=input_bytes,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise LandingRenderError("git_command") from exc
        if (
            completed.returncode != 0
            or len(completed.stdout) > 4 * 1_048_576
            or len(completed.stderr) > 1_048_576
        ):
            raise LandingRenderError("git_command")
        return completed.stdout


def _read_regular(path: Path) -> bytes:
    try:
        metadata = path.lstat()
        if not stat.S_ISREG(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
            raise LandingRenderError("workspace_file_type")
        if metadata.st_size <= 0 or metadata.st_size > MAX_LANDING_FILE_BYTES:
            raise LandingRenderError("workspace_file_size")
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            value = os.read(descriptor, MAX_LANDING_FILE_BYTES + 1)
        finally:
            os.close(descriptor)
    except OSError as exc:
        raise LandingRenderError("workspace_read") from exc
    if len(value) != metadata.st_size:
        raise LandingRenderError("workspace_read")
    return value


def _write_regular(path: Path, value: bytes) -> None:
    if not isinstance(value, bytes) or not value or len(value) > MAX_LANDING_FILE_BYTES:
        raise LandingRenderError("workspace_write")
    try:
        metadata = path.lstat()
        if not stat.S_ISREG(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
            raise LandingRenderError("workspace_file_type")
        descriptor = os.open(path, os.O_WRONLY | os.O_TRUNC | os.O_NOFOLLOW)
        try:
            view = memoryview(value)
            while view:
                written = os.write(descriptor, view)
                if written <= 0:
                    raise LandingRenderError("workspace_write")
                view = view[written:]
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except OSError as exc:
        raise LandingRenderError("workspace_write") from exc
