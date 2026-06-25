import os
import subprocess
from catkin_pkg.package import parse_package
from dataclasses import dataclass, field

@dataclass
class PackageMetadata:
    name: str
    path: str
    licenses: list[str] = field(default_factory=list)
    local_licenses: list[str] = field(default_factory=list)

@dataclass
class InspectionResult:
    top_level_licenses: list[str]
    packages: list[PackageMetadata]
    grep_names: str
    grep_licenses: str

class PackageInspector:
    """Inspects a local repository directory for ROS packages and licenses."""

    def __init__(self, repo_path: str):
        self.repo_path = repo_path

    def inspect(self) -> InspectionResult:
        """Runs all local inspections and returns an InspectionResult."""
        return InspectionResult(
            top_level_licenses=self.find_license_files("."),
            packages=self.find_ros_packages(),
            grep_names=self.run_grep_names(),
            grep_licenses=self.run_grep_licenses()
        )

    def find_license_files(self, relative_dir: str) -> list[str]:
        """Finds potential license files in a specific folder."""
        target_dir = os.path.join(self.repo_path, relative_dir)
        license_patterns = ["license", "copying"]
        found = []
        if not os.path.exists(target_dir):
            return found
            
        for name in os.listdir(target_dir):
            path = os.path.join(target_dir, name)
            if os.path.isfile(path):
                if any(pat in name.lower() for pat in license_patterns):
                    found.append(name)
        return found

    def find_ros_packages(self) -> list[PackageMetadata]:
        """Recursively scans the directory to find and parse ROS package.xml files."""
        packages = []
        for root, dirs, files in os.walk(self.repo_path):
            if "package.xml" in files:
                pkg_xml_path = os.path.join(root, "package.xml")
                rel_path = os.path.relpath(root, self.repo_path)
                if rel_path == ".":
                    rel_path = ""

                try:
                    pkg = parse_package(pkg_xml_path)
                    local_licenses = self.find_license_files(rel_path)
                    packages.append(
                        PackageMetadata(
                            name=pkg.name,
                            path=rel_path,
                            licenses=pkg.licenses,
                            local_licenses=local_licenses
                        )
                    )
                except Exception:
                    # Ignore invalid package.xmls
                    pass
        return packages

    def run_grep_names(self) -> str:
        """Runs find + grep for package name XML tags."""
        res = subprocess.run(
            'find . -name "package.xml" -exec grep --color=auto -e "<name>" "{}" ";"',
            shell=True,
            cwd=self.repo_path,
            capture_output=True,
            text=True,
        )
        return res.stdout.strip()

    def run_grep_licenses(self) -> str:
        """Runs find + grep for package license XML tags."""
        res = subprocess.run(
            'find . -name "package.xml" -exec grep --color=auto -e "<license>" "{}" "+"',
            shell=True,
            cwd=self.repo_path,
            capture_output=True,
            text=True,
        )
        return res.stdout.strip()
