import json
import sys
import requests
from .inspector import PackageMetadata

# The full text of REP-144 to provide to Gemini as context
REP_144_TEXT = """
REP: 144
title: ROS Package Naming
author: Vincent Rabaud
tag: Active
category: Informational
date: '2015-01-28'
---

## Abstract

This REP gives advice on how a ROS package should be named. It
formalizes and extends conventions that were formerly described in[^1].

## Motivation

As the number of ROS packages increases, it is hard to quickly find a
package and guess its functionality based on its name. Over time, the
lack of naming conventions created problems like use of unexplained
acronyms or packages with the same functionality but different names.

For now, ROS package names translate directly to packages in supported
Operating Systems: therefore, there is a flat global namespace in which
rules have to be followed.

This REP proposes rules to name a ROS package properly. Some of those
rules are mandatory, others merely advised.

## Package Naming

By habit, a package name is often used as a namespace (in C++ or any
other language). Thus, the naming rules have to be strict.

### Definitions

- `alphanumerics` are `a-z0-9` only
- `alphabetics` are `a-z` only

For clarity these are both specifically exclusively lowercase.

### Mandatory Rules

**A name must:**

- **only consist of lowercase alphanumerics and _ separators and start
  with an alphabetic character.** This allows it to be used in generated
  symbols and functions in all supported languages. Lowercase is
  required because the names are used in directories and filenames and
  some platforms do not have case sensitive filesystems.
- **not use multiple _ separators consecutively.** This allows
  generated symbols to use the `__` separator to guarenteed the
  avoidance of collisions with symbols from other packages, for example
  in the message generators.
- **be at least two characters long.** This rule is simply to force the
  name of the package to be more human understandable. It\'s recommended
  to be noteably longer, see below.

### Global Guidelines

- **Package names should be specific enough to identify what the package
  does.** For example, a motion planner should not be called `planner`.
  If it implements the wavefront propagation algorithm, it might be
  called `wavefront_planner`. There\'s obviously tension between making
  a name specific and keeping it from becoming overly verbose
- **Using catchall names such as** `utils` **should be avoided.** They
  do not scope what goes into the package or what should be outside the
  package
- **A package name should not contain** `ros` **as it is redundant.**
  Exceptions include core packages and ROS bindings of an upstream
  library (e.g. `moveit_ros`)
- **The package name should describe what the package does, but also
  avoid naming collisions.** Priority should be given to describing what
  the package does, but in an effort to avoid name collisions, packages
  which are primarily (at least to start with) used in a single project
  or organization should have a prefix with the project or organization
  name. One of ROS\'s goals is to develop a canonical set of tools for
  making robots do interesting things, however, as stated in the rules
  below,
  `if a package is specialized by an entity (...), prepend the name of the entity`.
  The preference is for packages to start namespaced and then once the
  package is commonly used, owned and maintained, that name can be
  dropped as the package becomes the reference. Exceptions for special
  situations where multiple organizations are collaborating on a
  package, or core packages, or official driver packages for hardware,
  and other special cases can be made. When prefixed by an entity the
  unprefixed name should follow the other rules about specificity and
  meaningful naming. This is a guideline, not a steadfast rule.
- **Do not use a name that\'s already been taken.** To check whether a
  name is taken, consult[^2]. If you\'d like your repository included in
  that list, see the tutorial at[^3]

### Naming Rules

The following rules define the different parts of the package name. The
overall idea is to prepend a name with words that distinguish it from
similar functional implementation (e.g.: `lab`, `robot`) but in order of
importance (e.g.: `python_robot_lab`). Similarly, words that specialize
this functionality are appended (e.g. `msgs`, `config`, ...).

The rules to add those words should be followed in order. For prefixes:

- if a package is specialized for a software project, prepend its name
- if a package is specialized for a hardware piece, prepend its name
- if a package is specialized for a robot, prepend its name
- if a package is specialized by an entity (lab, company, individual,
  ...), prepend the name of the entity. Once the package is commonly
  used, owned and maintained, that name can be dropped, but it should
  ideally start namespaced

For suffixes:

- if a package is a driver, append `driver`
- if a package contains any of a ROS message/service/action, append
  `msgs`
- if a package is a plugin for a library, append
  `<library_name>_plugins`, e.g. `pr2_gazebo_plugins`

Special Suffixes:

- a meta package for a robot should be named
  `<name_of_the_robot>_robot`, e.g. `pr2_robot`
- a package containing the URDF and meshes of a robot should be named
  `<name_of_the_robot>_description`, e.g `pr2_description`
- if a package is meant for test only, append `tests`

### Special Cases

- a package containing only a set of launch files should end with
  `launch`
- a package containing only a set of launch files whose goal is to start
  a robot should end with `bringup`
- a package containing one or more tutorials only should end with
  `tutorials`. If it is a set of tutorials for another package, it
  should contain that other package name: e.g. `navigation` and
  `navigation_tutorials`
- a package containing one or more demos only should end with `demos`
- third party libraries that are patched / integrated into ROS should
  not be named like their rosdep key as it creates a conflict across
  Ubuntu versions. If it is not specialized, name it generically
  `<name_of_library>_ros`

### Examples

The following is a list of examples following the above rules:

- A set of launch files for a wavefront planner, made for the PR2 by
  Willow Garage would have the following names when specializing the
  package more and more:
  - `planner_launch`
  - `wavefront_planner_launch`
  - `pr2_wavefront_planner_launch`
  - `willow_garage_pr2_wavefront_planner_launch`
- OpenCV 3 package, packaged for ROS: `opencv3_ros`
- a set of launch files for navigation tests:
  `navigation_launch_tests`
"""

class GeminiReviewer:
    """Invokes the Gemini API to review ROS packages naming and licenses."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    def review_packages(self, repo_name: str, packages: list[PackageMetadata]) -> dict:
        """Sends packages details to Gemini and parses the structured response."""
        print(f"Calling Gemini API to review package names and licenses for '{repo_name}'...", file=sys.stderr)

        packages_info = []
        for pkg in packages:
            packages_info.append(
                f"Package Name: {pkg.name}\n"
                f"Relative Path: {pkg.path or './'}\n"
                f"Declared Licenses in package.xml: {', '.join(pkg.licenses)}\n"
                f"Local License Files in package directory: {', '.join(pkg.local_licenses)}"
            )
        packages_info_str = "\n---\n".join(packages_info)

        prompt = f"""
You are an expert ROS reviewer. Your task is to evaluate the following ROS packages from a repository to check if they comply with the ROS package naming conventions (REP-144).

Here is the REP-144 specification:
---
{REP_144_TEXT}
---

Here are the packages found in the repository:
{packages_info_str}

Please evaluate:
1. For each package, does its name comply with the REP-144 rules and guidelines? Provide a boolean compliance flag (`rep_144_compliant`) and a brief, constructive explanation (`rep_144_comments`). Pay close attention to both mandatory rules and global guidelines, like:
   - Only lowercase alphanumerics and underscores, starting with an alphabetic.
   - No consecutive underscores.
   - At least 2 characters.
   - Specificity (e.g., avoiding generic names like 'planner' or 'utils').
   - Avoiding redundancy (e.g., not containing 'ros' unless it's a binding or core package).
   - Entity namespacing (prepending company/lab/user name if appropriate to avoid collisions).
   - Standard suffixes (like '_msgs', '_driver', '_plugins', '_description', etc.).

Please output your response in JSON format matching the following structure:
{{
  "packages": [
    {{
      "name": "package_name",
      "rep_144_compliant": true,
      "rep_144_comments": "Explanation of compliance or issues."
    }}
  ]
}}
"""

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"},
        }

        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            res_json = response.json()

            text = res_json["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(text)
        except Exception as e:
            print(f"Error calling Gemini API: {e}", file=sys.stderr)
            return {
                "error": str(e),
                "packages": [
                    {
                        "name": pkg.name,
                        "rep_144_compliant": False,
                        "rep_144_comments": f"Failed to call Gemini API: {e}",
                    }
                    for pkg in packages
                ],
            }
