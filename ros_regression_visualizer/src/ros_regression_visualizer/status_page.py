"""Parse ROS buildfarm status pages and extract package build/release status."""

from __future__ import annotations

from dataclasses import dataclass, field
import os
import re
from urllib.parse import parse_qs, urlparse, urlunparse

import requests


QUERY_TRANSFORMS: dict[str, str] = {
    "BLUE": 'class="l"',
    "ORANGE": 'class="h"',
    "RED": '<a class="m"',
    "YELLOW": 'class="o"',
    "GRAY": '<a class="i"',
    "RED1": '<td><a class="m"',
    "RED2": '</a><a class="m"|/><a class="m"',
    "RED3": '<a class="m"[^>]*></td>|<a class="m"/></td>',
    "ORPHANED": '<span class="unmaintained"|<span class="end-of-life"',
}


@dataclass(frozen=True)
class AptRepoStatus:
    """Status of a package in a single apt repository (building, testing, or main).

    Attributes:
        status_class: One of 'e' (same version), 'l' (lower version),
            'h' (higher version), 'm' (missing), 'o' (obsolete),
            'i' (intentionally missing).
        version_text: Raw version string from the square, if present
            (e.g. '4.3.0-5resolute' or '4.3.1-3resolute.20260929.155545').
    """

    status_class: str
    version_text: str = ""

    @property
    def clean_version(self) -> str:
        """Return the Debian version without trailing suite name or build timestamp."""
        if not self.version_text:
            return ""
        # Strip optional .YYYYMMDD.HHMMSS build timestamp first
        text = re.sub(r"\.\d{8}\.\d{6}$", "", self.version_text)
        # Strip trailing suite codename (e.g. 'resolute', 'noble', 'jammy', 'focal', 'buster')
        text = re.sub(r"[a-z]+$", "", text)
        return text

    @property
    def build_timestamp(self) -> str | None:
        """Extract the build timestamp (YYYYMMDD.HHMMSS) if present."""
        match = re.search(r"\.(\d{8}\.\d{6})$", self.version_text)
        return match.group(1) if match else None


@dataclass
class PackageStatus:
    """Parsed status row for a single ROS package on a buildfarm status page."""

    name: str
    repo_name: str
    repo_url: str
    version: str
    status: str
    maintainers: list[str] = field(default_factory=list)
    hidden_tags: set[str] = field(default_factory=set)
    source_column: tuple[AptRepoStatus, AptRepoStatus, AptRepoStatus] | None = None
    binary_columns: list[tuple[AptRepoStatus, AptRepoStatus, AptRepoStatus]] = field(
        default_factory=list
    )
    raw_html: str = ""

    @property
    def is_regression(self) -> bool:
        """Return True if the status page marked this package as a REGRESSION."""
        return "REGRESSION" in self.hidden_tags

    @property
    def is_failing(self) -> bool:
        """Return True if the package is a regression or missing in building/testing."""
        if self.is_regression:
            return True
        for col in self.binary_columns:
            # col[0] is building, col[1] is testing
            if col[0].status_class == "m" or col[1].status_class == "m":
                return True
        if self.source_column is not None:
            if (
                self.source_column[0].status_class == "m"
                or self.source_column[1].status_class == "m"
            ):
                return True
        return False

    @property
    def is_new_release(self) -> bool:
        """Return True if a new release of this package has been made since the last sync.

        On the ROS buildfarm status page, the 3rd square in each column represents the
        'main' apt repository (which was last updated at the previous sync):
        - status_class == 'l' means 'main' has a lower version than rosdistro (updated package).
        - status_class == 'm' when building/testing has 'e'/'l'/'h' (or 'SYNC' is in hidden_tags)
          means the package was newly added since the last sync.
        """
        if self.source_column is not None:
            building, testing, main = self.source_column
            if main.status_class == "l":
                return True
            if main.status_class == "m" and (
                building.status_class in ("e", "l", "h")
                or testing.status_class in ("e", "l", "h")
                or "SYNC" in self.hidden_tags
            ):
                return True
            return False

        for building, testing, main in self.binary_columns:
            if main.status_class == "l":
                return True
            if main.status_class == "m" and (
                building.status_class in ("e", "l", "h")
                or testing.status_class in ("e", "l", "h")
                or "SYNC" in self.hidden_tags
            ):
                return True
        return False

    @property
    def previous_version(self) -> str | None:
        """Return the version in 'main' if this package was updated from an older version."""
        if self.source_column is not None:
            main = self.source_column[2]
            if main.status_class == "l" and main.clean_version:
                return main.clean_version
        for col in self.binary_columns:
            main = col[2]
            if main.status_class == "l" and main.clean_version:
                return main.clean_version
        return None


def parse_status_page_arg(url_or_path: str) -> tuple[str, str | None]:
    """Split a `--status-page` argument into (base_url_or_path, query_string).

    Supports both HTTP(S) URLs and local file paths, with optional `?q=...` query parameters.
    """
    parsed = urlparse(url_or_path)
    query_str: str | None = None
    if parsed.query:
        qs = parse_qs(parsed.query, keep_blank_values=True)
        if "q" in qs and qs["q"]:
            query_str = qs["q"][0]

    if parsed.scheme in ("http", "https"):
        clean_url = urlunparse(
            (parsed.scheme, parsed.netloc, parsed.path, parsed.params, "", "")
        )
        return clean_url, query_str

    if parsed.scheme == "file":
        return parsed.path, query_str

    # Local path, possibly with ?q=... appended
    if "?" in url_or_path and not os.path.exists(url_or_path):
        base_path, _ = url_or_path.split("?", 1)
        return base_path, query_str

    return url_or_path, query_str


def fetch_status_page(base_url_or_path: str, timeout: float = 30.0) -> str:
    """Fetch status page HTML from an HTTP(S) URL or read from a local file path."""
    parsed = urlparse(base_url_or_path)
    if parsed.scheme in ("http", "https"):
        response = requests.get(base_url_or_path, timeout=timeout)
        response.raise_for_status()
        return response.text

    path = parsed.path if parsed.scheme == "file" else base_url_or_path
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def infer_distro_name(html: str, url_or_path: str = "") -> str:
    """Infer the ROS distribution name (e.g. 'lyrical') from status page HTML or URL."""
    # 1. Try <h2>ROS packages for <Distro></h2> or <title>ROS packages for <Distro>...
    heading_match = re.search(
        r"ROS packages for\s+([A-Za-z0-9_]+)", html, re.IGNORECASE
    )
    if heading_match:
        return heading_match.group(1).lower()

    # 2. Try package index links like https://index.ros.org/p/<pkg>#<distro>
    link_match = re.search(r'href="https?://index\.ros\.org/p/[^"#]+#([a-z0-9_]+)"', html)
    if link_match:
        return link_match.group(1).lower()

    # 3. Try filename convention ros_<distro>_*.html
    filename_match = re.search(r"ros_([a-z0-9]+)_[^/]+\.html", url_or_path)
    if filename_match:
        return filename_match.group(1).lower()

    raise ValueError(
        "Could not infer ROS distribution name from status page. "
        "Please specify --rosdistro explicitly."
    )


def _parse_apt_column(td_html: str) -> tuple[AptRepoStatus, AptRepoStatus, AptRepoStatus] | None:
    """Parse the 3 `<a>` tags (building, testing, main) inside a repo column `<td>`."""
    matches = re.findall(r'<a class="([^"]*)"(?:\s*/>|>([^<]*)</a>)', td_html)
    if len(matches) < 3:
        return None
    statuses = [
        AptRepoStatus(status_class=cls, version_text=ver)
        for cls, ver in matches[:3]
    ]
    return (statuses[0], statuses[1], statuses[2])


def parse_status_page_html(html: str) -> dict[str, PackageStatus]:
    """Parse all package rows from a ROS buildfarm status page HTML document."""
    # Identify which columns after the first 5 metadata columns are source vs binary
    # Example header: <th><div title="Ubuntu Resolute source">Rsource</div>...</th>
    thead_match = re.search(r"<thead>(.*?)</thead>", html, re.DOTALL)
    col_is_source: list[bool] = []
    if thead_match:
        th_blocks = re.findall(r"<th\b[^>]*>(.*?)</th>", thead_match.group(1), re.DOTALL)
        # First 5 columns are Name, Repo, Version, Status, Maintainer
        for th_content in th_blocks[5:]:
            div_match = re.search(
                r'<div(?:\s+title="([^"]*)")?[^>]*>([^<]*)</div>', th_content
            )
            if div_match:
                title_text = (div_match.group(1) or "").lower()
                label_text = (div_match.group(2) or "").lower()
                is_src = "source" in title_text or label_text.endswith("source")
                col_is_source.append(is_src)

    packages: dict[str, PackageStatus] = {}

    for line in html.splitlines():
        line_stripped = line.strip()
        if not line_stripped.startswith("<tr><td><div>"):
            continue

        tds = re.findall(r"<td(?:\s+[^>]*)?>(.*?)</td>", line_stripped)
        if len(tds) < 6:
            continue

        # Column 0: Package Name and hidden tags (<span class="ht">...</span>)
        name_td = tds[0]
        name_match = re.search(
            r"<div>(?:<a[^>]*>([^<]+)</a>|([^<]+))</div>", name_td
        )
        if not name_match:
            continue
        pkg_name = (name_match.group(1) or name_match.group(2) or "").strip()
        if not pkg_name:
            continue

        ht_match = re.search(r'<span class="ht">([^<]+)</span>', name_td)
        hidden_tags = set(ht_match.group(1).split()) if ht_match else set()

        # Column 1: Repository Name & URL
        repo_td = tds[1]
        repo_match = re.search(
            r'<div class="repo">(?:<a href="([^"]*)">([^<]+)</a>|([^<]+))</div>',
            repo_td,
        )
        if repo_match:
            repo_url = (repo_match.group(1) or "").strip()
            repo_name = (repo_match.group(2) or repo_match.group(3) or "").strip()
        else:
            repo_url = ""
            repo_name = ""

        # Column 2: Version in rosdistro
        ver_match = re.search(r"<span>([^<]+)</span>", tds[2])
        version = ver_match.group(1).strip() if ver_match else ""

        # Column 3: Status (e.g. <span class="developed"/> or <span class="maintained"/>)
        status_match = re.search(r'<span class="([^"]+)"', tds[3])
        status = status_match.group(1).strip() if status_match else ""

        # Column 4: Maintainers
        maintainers = re.findall(r"<a[^>]*>([^<]+)</a>", tds[4])

        # Columns 5+: Source and Binary apt repository columns
        source_col: tuple[AptRepoStatus, AptRepoStatus, AptRepoStatus] | None = None
        binary_cols: list[tuple[AptRepoStatus, AptRepoStatus, AptRepoStatus]] = []

        apt_tds = tds[5:]
        for idx, apt_td in enumerate(apt_tds):
            parsed_col = _parse_apt_column(apt_td)
            if parsed_col is None:
                continue
            is_src = (
                col_is_source[idx]
                if idx < len(col_is_source)
                else (idx == 0 and len(apt_tds) > 1)
            )
            if is_src and source_col is None:
                source_col = parsed_col
            else:
                binary_cols.append(parsed_col)

        packages[pkg_name] = PackageStatus(
            name=pkg_name,
            repo_name=repo_name,
            repo_url=repo_url,
            version=version,
            status=status,
            maintainers=maintainers,
            hidden_tags=hidden_tags,
            source_column=source_col,
            binary_columns=binary_cols,
            raw_html=line_stripped,
        )

    return packages


def filter_packages_by_query(
    packages: dict[str, PackageStatus],
    query: str | None = None,
) -> set[str]:
    """Filter packages using the status page's `?q=...` query syntax.

    If `query` is None or empty, defaults to `'REGRESSION'`.
    Supports `+`-separated query parts, magic queries (`REGRESSION`, `SYNC`,
    `DIFF`, `BLUE`, `ORANGE`, `RED`, `YELLOW`, `GRAY`, `ORPHANED`), and regular
    expressions matching package metadata.
    """
    effective_query = query if (query is not None and query.strip()) else "REGRESSION"
    raw_parts = [p for p in effective_query.split("+") if len(p) >= 3]
    if not raw_parts:
        raw_parts = [effective_query.strip()]

    matched: set[str] = set()
    for pkg_name, pkg in packages.items():
        all_satisfied = True
        for part in raw_parts:
            if part in QUERY_TRANSFORMS:
                pattern = QUERY_TRANSFORMS[part]
                if not re.search(pattern, pkg.raw_html):
                    all_satisfied = False
                    break
            else:
                # Search plain text fields of metadata columns (matching status_page_setup.js)
                searchable_fields = [
                    f"{pkg.name} {' '.join(sorted(pkg.hidden_tags))}",
                    pkg.repo_name,
                    pkg.version,
                    pkg.status,
                    " ".join(pkg.maintainers) + " " + " ".join(m.lower() for m in pkg.maintainers),
                ]
                if not any(re.search(part, field) for field in searchable_fields):
                    all_satisfied = False
                    break
        if all_satisfied:
            matched.add(pkg_name)

    return matched
