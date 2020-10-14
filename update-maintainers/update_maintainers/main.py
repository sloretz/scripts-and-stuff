import argparse
from collections import defaultdict
import pathlib

import re

from defusedxml import ElementTree

xml = """<?xml version="1.0"?>
<package>
  <name>ros_tutorials</name>
  <version>0.10.2</version>
  <description>
    ros_tutorials contains packages that demonstrate various features of ROS,
    as well as support packages which help demonstrate those features.
  </description>
  <maintainer email="dthomas@osrfoundation.org">Dirk Thomas</maintainer>
  <license>BSD</license>

  <url type="website">http://www.ros.org/wiki/ros_tutorials</url>
  <url type="bugtracker">https://github.com/ros/ros_tutorials/issues</url>
  <url type="repository">https://github.com/ros/ros_tutorials</url>
  <author>Josh Faust</author>
  <author>Ken Conley</author>

  <buildtool_depend>catkin</buildtool_depend>

  <run_depend>roscpp_tutorials</run_depend>
  <run_depend>rospy_tutorials</run_depend>
  <run_depend>turtlesim</run_depend>

  <export>
    <metapackage/>
  </export>
</package>
"""


def parse_package_xml(package_xml_str):
    root = ElementTree.fromstring(package_xml_str)
    if 'package' != root.tag:
        raise ValueError('Expecting root tag to be <package...>')
    return root

def same_person(alice_pair, bob_pair):
    alice_name, alice_email = alice_pair[0], alice_pair[1]
    bob_name, bob_email = bob_pair[0], bob_pair[1]

    if alice_email.strip() and alice_email.strip().lower() == bob_email.strip().lower():
        return True
    if alice_name.strip().lower().replace(' ', '') == bob_name.strip().lower().replace(' ', ''):
        return True
    return False


def insert_at(insert_text, text, text_idx):
    return text[:text_idx] + insert_text + text[text_idx:]


def main():
    parser = argparse.ArgumentParser(description='Update package maintainers')
    parser.add_argument('path_to_package_xml', metavar='PATH',
                        help='A path to a package.xml file')
    parser.add_argument('--maintainer', nargs=1, action='append',
                        required=True, metavar="EMAIL:name",
                        help='The new maintainer for this package.xml')
    parser.add_argument('--output', type=str, default='-', nargs='?',
                        help='Where the updated package.xml will be written to (default stdout)')
    parser.add_argument('--alphabetize-authors', default=False, action='store_true',
                        help='Alphabetically order the author list')

    args = parser.parse_args()

    # Clean up arguments
    new_maintainers = []
    for maintainer in args.maintainer:
        maintainer = maintainer[0].split(':')
        if 2 != len(maintainer):
            raise ValueError('--maintainer must be in given as "email:full name"')
        # email, name -> name, email
        maintainer = maintainer[1], maintainer[0]
        new_maintainers.append(maintainer)

    # Read in package.xml
    with open(args.path_to_package_xml, 'r') as fin:
        package_xml_str = fin.read()
        package = parse_package_xml(package_xml_str)

    # Determine what changes need to be made
    authors_to_add = []
    existing_maintainers = []
    for tag in package.findall('maintainer'):
        existing_maintainer = (tag.text, tag.attrib.get('email', ''))
        existing_maintainers.append(existing_maintainer)
        found = False
        for new_maintainer in new_maintainers:
            if same_person(new_maintainer, existing_maintainer):
                found = True
        if not found:
            authors_to_add.append(existing_maintainer)

    # Remove all maintainers from package.xml, then re-add them
    for full_name, email in existing_maintainers:
        expr = '[\s]*<maintainer[\s]+email="{email}">{full_name}</maintainer[\s]*>'.format(
            email=email, full_name=full_name)
        package_xml_str = re.sub(expr, '', package_xml_str)

    license_idx = package_xml_str.find('<license')
    if license_idx < 0:
        raise ValueError('Cannot update package.xml if it is missing a <license> tag')
    # Determine whitespace to add
    whitespace_idx = license_idx - 1
    while package_xml_str[whitespace_idx] in (' ', '\t'):
        whitespace_idx -= 1
    # don't include last newline
    whitespace_idx += 1
    whitespace = package_xml_str[whitespace_idx:license_idx]

    for full_name, email in sorted(new_maintainers, reverse=True):
        line = f'{whitespace}<maintainer email="{email}">{full_name}</maintainer>\n'
        # Insert just before license text line
        package_xml_str = insert_at(line, package_xml_str, whitespace_idx)

    # Find all authors from the package.xml so we don't add duplicates
    existing_authors = []
    author_expr = f'[ \t]*<author([\s]+email="(?P<email>.+)")?>(?P<full_name>.+)</author[\s]*>[ \t]*\n'
    for match in re.finditer(author_expr, package_xml_str):
        name = match.group('full_name')
        email = match.group('email')
        if email is None:
            email = ''
        existing_authors.append((name, email))

    if args.alphabetize_authors:
        # Remove all authors from package.xml
        for full_name, email in existing_authors:
            expr = '[\s]*<author([\s]+email="{email}")?>{full_name}</author[\s]*>'.format(
                email=email, full_name=full_name)
            package_xml_str = re.sub(expr, '', package_xml_str)
            authors_to_add.append((name, email))
        # There are no existing authors because they were all removed
        existing_authors.clear()

    # Don't add authors that are already present
    for existing_author in existing_authors:
        found = False
        for new_author in authors_to_add:
            if same_person(new_author, existing_author):
                authors_to_add.remove(new_author)
                break

    if authors_to_add:
        # Determine where to add authors (Either after last author, <url>, or license)
        author_idx = package_xml_str.rfind('</author>')
        url_idx = package_xml_str.rfind('</url>')
        license_idx = package_xml_str.rfind('</license>')
        if author_idx >= 0:
            insert_idx = author_idx + len('</author>')
        elif url_idx >= 0:
            insert_idx = url_idx + len('</url>')
        elif license_idx >= 0:
            insert_idx = license_idx + len('</license>')
        else:
            raise RuntimeError('Could not find end of license or url tags')

        # Insert after newline
        if package_xml_str[insert_idx] != '\n':
            raise RuntimeError(f'{args.path_to_package_xml} trailing whitespace after <url> or <license>')

        insert_idx += 1

        for full_name, email in sorted(authors_to_add, reverse=True):
            if email:
                line = f'{whitespace}<author email="{email}">{full_name}</author>\n'
            else:
                line = f'{whitespace}<author>{full_name}</author>\n'
            package_xml_str = insert_at(line, package_xml_str, insert_idx)

    if '-' == args.output:
        print(package_xml_str)
    else:
        with open(args.output, 'w') as fout:
            fout.write(package_xml_str)


if __name__ == '__main__':
    main()
