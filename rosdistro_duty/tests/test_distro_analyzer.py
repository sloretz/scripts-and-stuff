import pytest
from rosdistro_duty.distro_analyzer import DistroDiffAnalyzer

def test_find_modified_repositories():
    base_yaml = """
    repositories:
      repo_a:
        doc:
          type: git
          url: https://github.com/ros/repo_a.git
          version: main
        source:
          type: git
          url: https://github.com/ros/repo_a.git
          version: main
      repo_b:
        source:
          type: git
          url: https://github.com/ros/repo_b.git
          version: melodic-devel
    """

    # repo_a: unmodified source
    # repo_b: modified source version (melodic-devel -> noetic-devel)
    # repo_c: newly added repository with source
    # repo_d: newly added repository without source (only release)
    head_yaml = """
    repositories:
      repo_a:
        doc:
          type: git
          url: https://github.com/ros/repo_a.git
          version: main
        source:
          type: git
          url: https://github.com/ros/repo_a.git
          version: main
      repo_b:
        source:
          type: git
          url: https://github.com/ros/repo_b.git
          version: noetic-devel
      repo_c:
        source:
          type: git
          url: https://github.com/ros/repo_c.git
          version: main
      repo_d:
        release:
          url: https://github.com/ros/repo_d-release.git
          version: 1.0.0-0
    """

    analyzer = DistroDiffAnalyzer()
    modified = analyzer.find_modified_repositories(head_yaml, base_yaml)

    # We expect:
    # - repo_b: because version changed
    # - repo_c: because it is new and has a source stanza
    # - NOT repo_a (unmodified)
    # - NOT repo_d (no source stanza)
    assert len(modified) == 2
    assert "repo_b" in modified
    assert "repo_c" in modified
    assert "repo_a" not in modified
    assert "repo_d" not in modified

    assert modified["repo_b"]["version"] == "noetic-devel"
    assert modified["repo_c"]["url"] == "https://github.com/ros/repo_c.git"
