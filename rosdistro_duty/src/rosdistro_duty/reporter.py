import os
from .inspector import InspectionResult

def make_github_file_url(repo_url: str, version: str, relative_path: str) -> str:
    """Constructs a GitHub blob URL for a specific file in the repository."""
    base_url = repo_url.strip()
    if base_url.endswith(".git"):
        base_url = base_url[:-4]
    
    # Ensure relative path doesn't start with / and uses forward slashes
    rel_path = relative_path.strip().replace(os.sep, "/").lstrip("/")
    
    return f"{base_url}/blob/{version}/{rel_path}"

class MarkdownReportGenerator:
    """Generates the markdown review checklist from inspection and Gemini review results."""

    def generate(
        self,
        repo_id: str,
        url: str,
        version: str,
        inspection: InspectionResult,
        gemini_results: dict,
    ) -> str:
        """Assembles the complete markdown checklist report."""
        # Check if the root directory itself is a ROS package
        is_root_a_package = any(p.path == "" for p in inspection.packages)

        if is_root_a_package:
            top_level_checked = False
            top_level_status = "No (root directory is a ROS package)"
        else:
            top_level_checked = len(inspection.top_level_licenses) > 0
            top_level_links = [
                f"[{name}]({make_github_file_url(url, version, name)})"
                for name in inspection.top_level_licenses
            ]
            top_level_status = (
                f"Yes (found {', '.join(top_level_links)})"
                if top_level_checked
                else "No"
            )

        packages_with_license = [
            p.name for p in inspection.packages if p.local_licenses
        ]
        per_package_checked = len(packages_with_license) > 0
        
        per_package_links = []
        for p in inspection.packages:
            if p.local_licenses:
                # Link to the first license file found in this package
                lic_path = os.path.join(p.path, p.local_licenses[0])
                lic_url = make_github_file_url(url, version, lic_path)
                per_package_links.append(f"[{p.name}]({lic_url})")
                
        per_package_status = (
            f"Yes (found in packages: {', '.join(per_package_links)})"
            if per_package_checked
            else "No"
        )

        at_least_one_checked = top_level_checked or per_package_checked



        public_repo_status = "Yes"
        public_repo_checked = True

        contains_packages = len(inspection.packages) > 0
        contains_ros_packages_status = (
            f"Yes (found {len(inspection.packages)} package(s))"
            if contains_packages
            else "No"
        )
        contains_ros_packages_checked = contains_packages

        packages_eval = gemini_results.get("packages", [])
        # Map Gemini package evaluations by package name
        gemini_pkg_map = {}
        for p_eval in packages_eval:
            gemini_pkg_map[p_eval.get("name")] = p_eval

        def box(b: bool) -> str:
            return "[x]" if b else "[ ]"

        # Generate repository level checks
        lines = [
            "---",
            f"# Review for repository: `{repo_id}`",
            f"Source URL: {url} (version: {version})",
            "",
            "## New package review checklist",
            "",
            "### Repository level checks",
            f"- {box(public_repo_checked)} Public source repo: {public_repo_status}",
            f"- {box(contains_ros_packages_checked)} Source repository contains ROS packages: {contains_ros_packages_status}",
            f"- {box(at_least_one_checked)} At least one of the following must be present",
            f"  - {box(top_level_checked)} Top level license file: {top_level_status}",
            f"  - {box(per_package_checked)} Per package license files: {per_package_status}",
            "",
            "### Package level checks",
            ""
        ]

        # Generate package level checks for each package
        if inspection.packages:
            for p in inspection.packages:
                p_eval = gemini_pkg_map.get(p.name, {})
                
                # Naming check
                rep_144_ok = p_eval.get("rep_144_compliant", True)
                rep_144_status = "Yes" if rep_144_ok else "No"
                
                # OSI approved check (always unchecked, manual TODO)
                lics_str = f" ({', '.join(p.licenses)})" if p.licenses else ""
                osi_status = f"TODO 🚧{lics_str}"
                
                # package.xml license check
                xml_ok = len(p.licenses) > 0
                xml_status = "Yes" if xml_ok else "No"
                
                # package.xml link
                xml_rel_path = os.path.join(p.path, "package.xml")
                xml_url = make_github_file_url(url, version, xml_rel_path)
                
                lines.extend([
                    f"##### Package: `{p.name}`",
                    f"- {box(rep_144_ok)} Meets [REP-144](https://reps.openrobotics.org/rep-0144/) naming conventions: {rep_144_status}",
                    f"- [ ] License is [OSI-approved](https://opensource.org/licenses): {osi_status}",
                    f"- {box(xml_ok)} License correctly listed in [package.xml]({xml_url}): {xml_status}",
                    ""
                ])
        else:
            lines.append("No packages found.")
            lines.append("")
        lines.extend([
            "",
            "<details><summary>Package name details</summary>",
            "",
            "```console",
            '$ find . -name "package.xml" -exec grep --color=auto -e "<name>" "{}" ";"',
        ])
        if inspection.grep_names:
            lines.append(inspection.grep_names)
        lines.extend([
            "```",
            "</details>",
            "",
            "<details><summary>License details</summary>",
            "",
            "```console",
            '$ find . -name "package.xml" -exec grep --color=auto -e "<license>" "{}" "+"',
        ])
        if inspection.grep_licenses:
            lines.append(inspection.grep_licenses)
        lines.extend([
            "```",
            "</details>",
            "",
            "<details><summary>Detailed review by Gemini</summary>",
            "",
            "### Naming Review (Gemini Feedback)",
            ""
        ])

        feedback_parts = []
        for pkg in packages_eval:
            pkg_name = pkg.get("name")
            rep_144_val = (
                "Compliant" if pkg.get("rep_144_compliant") else "Non-compliant"
            )
            rep_comments = pkg.get("rep_144_comments", "")

            feedback_parts.append(
                f"#### Package: `{pkg_name}`\n"
                f"- **REP-144 Naming**: {rep_144_val}\n"
                f"  *Comments:* {rep_comments}"
            )

        lines.append("\n\n".join(feedback_parts))
        lines.extend([
            "</details>",
            "",
        ])

        return "\n".join(lines)

