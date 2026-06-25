import os
import pytest
from rosdistro_duty.inspector import PackageInspector, PackageMetadata

def test_find_license_files(tmp_path):
    # Create mock license files in the temp directory
    (tmp_path / "LICENSE").write_text("Mock License")
    (tmp_path / "COPYING.txt").write_text("Mock Copying")
    (tmp_path / "README.md").write_text("Mock Readme")
    (tmp_path / "other_file.py").write_text("print(1)")

    inspector = PackageInspector(str(tmp_path))
    licenses = inspector.find_license_files(".")
    
    assert len(licenses) == 2
    assert "LICENSE" in licenses
    assert "COPYING.txt" in licenses
    assert "README.md" not in licenses

def test_find_ros_packages(tmp_path):
    # Create two package subdirectories
    pkg_a_dir = tmp_path / "pkg_a"
    pkg_a_dir.mkdir()
    pkg_b_dir = tmp_path / "pkg_b"
    pkg_b_dir.mkdir()
    
    # Write a multi-license package.xml in pkg_a
    pkg_a_xml = """<?xml version="1.0"?>
    <package format="3">
      <name>my_cool_pkg_a</name>
      <version>0.1.0</version>
      <description>Test description A</description>
      <maintainer email="a@a.com">Maintainer A</maintainer>
      <license>Apache-2.0</license>
      <license>MIT</license>
    </package>
    """
    (pkg_a_dir / "package.xml").write_text(pkg_a_xml)
    (pkg_a_dir / "LICENSE").write_text("Local license")

    # Write a single-license package.xml in pkg_b
    pkg_b_xml = """<?xml version="1.0"?>
    <package format="2">
      <name>my_cool_pkg_b</name>
      <version>1.0.0</version>
      <description>Test description B</description>
      <maintainer email="b@b.com">Maintainer B</maintainer>
      <license>BSD-3-Clause</license>
    </package>
    """
    (pkg_b_dir / "package.xml").write_text(pkg_b_xml)

    inspector = PackageInspector(str(tmp_path))
    packages = inspector.find_ros_packages()

    # Sort packages by name to guarantee order
    packages = sorted(packages, key=lambda p: p.name)

    assert len(packages) == 2
    
    # Verify pkg_a
    assert packages[0].name == "my_cool_pkg_a"
    assert packages[0].path == "pkg_a"
    assert set(packages[0].licenses) == {"Apache-2.0", "MIT"}
    assert "LICENSE" in packages[0].local_licenses

    # Verify pkg_b
    assert packages[1].name == "my_cool_pkg_b"
    assert packages[1].path == "pkg_b"
    assert packages[1].licenses == ["BSD-3-Clause"]
    assert len(packages[1].local_licenses) == 0
