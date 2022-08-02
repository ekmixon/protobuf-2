#!/usr/bin/env python
# Usage: ./update_version.py <MAJOR>.<MINOR>.<MICRO> [<RC version>]
#
# Example:
# ./update_version.py 3.7.1 2
#   => Version will become 3.7.1-rc-2 (beta)
# ./update_version.py 3.7.1
#   => Version will become 3.7.1 (stable)

import datetime
import re
import sys
from xml.dom import minidom

if len(sys.argv) < 2 or len(sys.argv) > 3:
  print("""
[ERROR] Please specify a version.

./update_version.py <MAJOR>.<MINOR>.<MICRO> [<RC version>]

Example:
./update_version.py 3.7.1 2
""")
  exit(1)

NEW_VERSION = sys.argv[1]
NEW_VERSION_INFO = [int(x) for x in NEW_VERSION.split('.')]
if len(NEW_VERSION_INFO) != 3:
  print("""
[ERROR] Version must be in the format <MAJOR>.<MINOR>.<MICRO>

Example:
./update_version.py 3.7.3
""")
  exit(1)

RC_VERSION = int(sys.argv[2]) if len(sys.argv) > 2 else -1


def Find(elem, tagname):
  return next(
      (child for child in elem.childNodes if child.nodeName == tagname), None)


def FindAndClone(elem, tagname):
  return Find(elem, tagname).cloneNode(True)


def ReplaceText(elem, text):
  elem.firstChild.replaceWholeText(text)


def GetFullVersion(rc_suffix = '-rc-'):
  if RC_VERSION < 0:
    return NEW_VERSION
  else:
    return f'{NEW_VERSION}{rc_suffix}{RC_VERSION}'


def GetSharedObjectVersion():
  protobuf_version_offset = 11
  expected_major_version = 3
  if NEW_VERSION_INFO[0] != expected_major_version:
    print("""[ERROR] Major protobuf version has changed. Please update
update_version.py to readjust the protobuf_version_offset and
expected_major_version such that the PROTOBUF_VERSION in src/Makefile.am is
always increasing.
    """)
    exit(1)
  return [NEW_VERSION_INFO[1] + protobuf_version_offset, NEW_VERSION_INFO[2], 0]


def RewriteXml(filename, rewriter, add_xml_prefix=True):
  document = minidom.parse(filename)
  rewriter(document)
  # document.toxml() always prepend the XML version without inserting new line.
  # We wants to preserve as much of the original formatting as possible, so we
  # will remove the default XML version and replace it with our custom one when
  # whever necessary.
  content = document.toxml().replace('<?xml version="1.0" ?>', '')
  with open(filename, 'wb') as file_handle:
    if add_xml_prefix:
      file_handle.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
    file_handle.write(content.encode('utf-8'))
    file_handle.write(b'\n')


def RewriteTextFile(filename, line_rewriter):
  lines = open(filename, 'r').readlines()
  updated_lines = [line_rewriter(line) for line in lines]
  if lines == updated_lines:
    print(f'{filename} was not updated. Please double check.')
  with open(filename, 'w') as f:
    f.write(''.join(updated_lines))


def UpdateCMake():
  cmake_files = (
    'cmake/libprotobuf.cmake',
    'cmake/libprotobuf-lite.cmake',
    'cmake/libprotoc.cmake'
  )
  for cmake_file in cmake_files:
    RewriteTextFile(
        cmake_file,
        lambda line: re.sub(
            r'SOVERSION ([0-9]+)$',
            f'SOVERSION {GetSharedObjectVersion()[0]}',
            line,
        ),
    )


def UpdateConfigure():
  RewriteTextFile(
      'configure.ac',
      lambda line: re.sub(
          r'^AC_INIT\(\[Protocol Buffers\],\[.*\],\[protobuf@googlegroups.com\],\[protobuf\]\)$',
          f'AC_INIT([Protocol Buffers],[{GetFullVersion()}],[protobuf@googlegroups.com],[protobuf])',
          line,
      ),
  )


def UpdateCpp():
  cpp_version = '%d%03d%03d' % (
    NEW_VERSION_INFO[0], NEW_VERSION_INFO[1], NEW_VERSION_INFO[2])
  version_suffix = ''
  if RC_VERSION != -1:
    version_suffix = f'-rc{RC_VERSION}'
  def RewriteCommon(line):
    line = re.sub(
        r'^#define GOOGLE_PROTOBUF_VERSION .*$',
        f'#define GOOGLE_PROTOBUF_VERSION {cpp_version}',
        line,
    )
    line = re.sub(
        r'^#define PROTOBUF_VERSION .*$',
        f'#define PROTOBUF_VERSION {cpp_version}',
        line,
    )
    line = re.sub(
        r'^#define GOOGLE_PROTOBUF_VERSION_SUFFIX .*$',
        '#define GOOGLE_PROTOBUF_VERSION_SUFFIX "%s"' % version_suffix,
        line)
    line = re.sub(
        r'^#define PROTOBUF_VERSION_SUFFIX .*$',
        '#define PROTOBUF_VERSION_SUFFIX "%s"' % version_suffix,
        line)
    if NEW_VERSION_INFO[2] == 0:
      line = re.sub(
          r'^#define PROTOBUF_MIN_HEADER_VERSION_FOR_PROTOC .*$',
          f'#define PROTOBUF_MIN_HEADER_VERSION_FOR_PROTOC {cpp_version}',
          line,
      )
      line = re.sub(
          r'^#define GOOGLE_PROTOBUF_MIN_PROTOC_VERSION .*$',
          f'#define GOOGLE_PROTOBUF_MIN_PROTOC_VERSION {cpp_version}',
          line,
      )
      line = re.sub(
          r'^static const int kMinHeaderVersionForLibrary = .*$',
          f'static const int kMinHeaderVersionForLibrary = {cpp_version};',
          line,
      )
      line = re.sub(
          r'^static const int kMinHeaderVersionForProtoc = .*$',
          f'static const int kMinHeaderVersionForProtoc = {cpp_version};',
          line,
      )
    return line

  def RewritePortDef(line):
    line = re.sub(
        r'^#define PROTOBUF_VERSION .*$',
        f'#define PROTOBUF_VERSION {cpp_version}',
        line,
    )
    line = re.sub(
        r'^#define PROTOBUF_VERSION_SUFFIX .*$',
        '#define PROTOBUF_VERSION_SUFFIX "%s"' % version_suffix,
        line)
    if NEW_VERSION_INFO[2] == 0:
      line = re.sub(
          r'^#define PROTOBUF_MIN_HEADER_VERSION_FOR_PROTOC .*$',
          f'#define PROTOBUF_MIN_HEADER_VERSION_FOR_PROTOC {cpp_version}',
          line,
      )
      line = re.sub(
          r'^#define PROTOBUF_MIN_PROTOC_VERSION .*$',
          f'#define PROTOBUF_MIN_PROTOC_VERSION {cpp_version}',
          line,
      )
      line = re.sub(
          r'^#define GOOGLE_PROTOBUF_MIN_LIBRARY_VERSION .*$',
          f'#define GOOGLE_PROTOBUF_MIN_LIBRARY_VERSION {cpp_version}',
          line,
      )
    return line

  def RewritePbH(line):
    line = re.sub(
        r'^#if PROTOBUF_VERSION < .*$',
        f'#if PROTOBUF_VERSION < {cpp_version}',
        line,
    )
    line = re.sub(
        r'^#if .* < PROTOBUF_MIN_PROTOC_VERSION$',
        f'#if {cpp_version} < PROTOBUF_MIN_PROTOC_VERSION',
        line,
    )
    return line

  RewriteTextFile('src/google/protobuf/stubs/common.h', RewriteCommon)
  RewriteTextFile('src/google/protobuf/port_def.inc', RewritePortDef)
  RewriteTextFile('src/google/protobuf/any.pb.h', RewritePbH)
  RewriteTextFile('src/google/protobuf/api.pb.h', RewritePbH)
  RewriteTextFile('src/google/protobuf/descriptor.pb.h', RewritePbH)
  RewriteTextFile('src/google/protobuf/duration.pb.h', RewritePbH)
  RewriteTextFile('src/google/protobuf/empty.pb.h', RewritePbH)
  RewriteTextFile('src/google/protobuf/field_mask.pb.h', RewritePbH)
  RewriteTextFile('src/google/protobuf/source_context.pb.h', RewritePbH)
  RewriteTextFile('src/google/protobuf/struct.pb.h', RewritePbH)
  RewriteTextFile('src/google/protobuf/timestamp.pb.h', RewritePbH)
  RewriteTextFile('src/google/protobuf/type.pb.h', RewritePbH)
  RewriteTextFile('src/google/protobuf/wrappers.pb.h', RewritePbH)
  RewriteTextFile('src/google/protobuf/compiler/plugin.pb.h', RewritePbH)


def UpdateCsharp():
  RewriteXml('csharp/src/Google.Protobuf/Google.Protobuf.csproj',
    lambda document : ReplaceText(
      Find(Find(document.documentElement, 'PropertyGroup'), 'VersionPrefix'),
      GetFullVersion(rc_suffix = '-rc')),
    add_xml_prefix=False)

  RewriteXml('csharp/Google.Protobuf.Tools.nuspec',
    lambda document : ReplaceText(
      Find(Find(document.documentElement, 'metadata'), 'version'),
      GetFullVersion(rc_suffix = '-rc')))


def UpdateJava():
  RewriteXml('java/pom.xml',
    lambda document : ReplaceText(
      Find(document.documentElement, 'version'), GetFullVersion()))

  RewriteXml('java/bom/pom.xml',
    lambda document : ReplaceText(
      Find(document.documentElement, 'version'), GetFullVersion()))

  RewriteXml('java/core/pom.xml',
    lambda document : ReplaceText(
      Find(Find(document.documentElement, 'parent'), 'version'),
      GetFullVersion()))

  RewriteXml('java/lite/pom.xml',
    lambda document : ReplaceText(
      Find(Find(document.documentElement, 'parent'), 'version'),
      GetFullVersion()))

  RewriteXml('java/util/pom.xml',
    lambda document : ReplaceText(
      Find(Find(document.documentElement, 'parent'), 'version'),
      GetFullVersion()))

  RewriteXml('java/kotlin/pom.xml',
    lambda document : ReplaceText(
      Find(Find(document.documentElement, 'parent'), 'version'),
      GetFullVersion()))

  RewriteXml('java/kotlin-lite/pom.xml',
    lambda document : ReplaceText(
      Find(Find(document.documentElement, 'parent'), 'version'),
      GetFullVersion()))

  RewriteXml('protoc-artifacts/pom.xml',
    lambda document : ReplaceText(
      Find(document.documentElement, 'version'), GetFullVersion()))

  RewriteTextFile(
      'java/README.md',
      lambda line: re.sub(
          r'<version>.*</version>',
          f'<version>{GetFullVersion()}</version>',
          line,
      ),
  )

  RewriteTextFile('java/README.md',
    lambda line : re.sub(
      r'implementation \'com.google.protobuf:protobuf-java:.*\'',
      'implementation \'com.google.protobuf:protobuf-java:%s\'' % GetFullVersion(),
      line))

  RewriteTextFile(
      'java/lite.md',
      lambda line: re.sub(
          r'<version>.*</version>',
          f'<version>{GetFullVersion()}</version>',
          line,
      ),
  )


def UpdateJavaScript():
  RewriteTextFile('js/package.json',
    lambda line : re.sub(
      r'^  "version": ".*",$',
      '  "version": "%s",' % GetFullVersion(rc_suffix = '-rc.'),
      line))


def UpdateMakefile():
  RewriteTextFile(
      'src/Makefile.am',
      lambda line: re.sub(
          r'^PROTOBUF_VERSION = .*$',
          f'PROTOBUF_VERSION = {":".join(map(str,GetSharedObjectVersion()))}',
          line,
      ),
  )


def UpdateObjectiveC():
  RewriteTextFile('Protobuf.podspec',
    lambda line : re.sub(
      r"^  s.version  = '.*'$",
      "  s.version  = '%s'" % GetFullVersion(rc_suffix = '-rc'),
      line))
  RewriteTextFile('Protobuf-C++.podspec',
    lambda line : re.sub(
      r"^  s.version  = '.*'$",
      "  s.version  = '%s'" % GetFullVersion(rc_suffix = '-rc'),
      line))


def UpdatePhp():
  def Callback(document):
    def CreateNode(tagname, indent, children):
      elem = document.createElement(tagname)
      indent += 1
      for child in children:
        elem.appendChild(document.createTextNode('\n' + (' ' * indent)))
        elem.appendChild(child)
      indent -= 1
      elem.appendChild(document.createTextNode('\n' + (' ' * indent)))
      return elem

    root = document.documentElement
    now = datetime.datetime.now()
    ReplaceText(Find(root, 'date'), now.strftime('%Y-%m-%d'))
    ReplaceText(Find(root, 'time'), now.strftime('%H:%M:%S'))
    version = Find(root, 'version')
    ReplaceText(Find(version, 'release'), GetFullVersion(rc_suffix = 'RC'))
    ReplaceText(Find(version, 'api'), NEW_VERSION)
    stability = Find(root, 'stability')
    ReplaceText(Find(stability, 'release'),
        'stable' if RC_VERSION < 0 else 'beta')
    ReplaceText(Find(stability, 'api'), 'stable' if RC_VERSION < 0 else 'beta')
    changelog = Find(root, 'changelog')
    for old_version in changelog.getElementsByTagName('version'):
      if Find(old_version, 'release').firstChild.nodeValue == NEW_VERSION:
        print(f'[WARNING] Version {NEW_VERSION} already exists in the change log.')
        return
    if RC_VERSION != 0:
      changelog.appendChild(document.createTextNode(' '))
      release = CreateNode('release', 2, [
          CreateNode('version', 3, [
            FindAndClone(version, 'release'),
            FindAndClone(version, 'api')
          ]),
          CreateNode('stability', 3, [
            FindAndClone(stability, 'release'),
            FindAndClone(stability, 'api')
          ]),
          FindAndClone(root, 'date'),
          FindAndClone(root, 'time'),
          FindAndClone(root, 'license'),
          CreateNode('notes', 3, []),
        ])
      changelog.appendChild(release)
      changelog.appendChild(document.createTextNode('\n '))

  RewriteXml('php/ext/google/protobuf/package.xml', Callback)
  RewriteTextFile('php/ext/google/protobuf/protobuf.h',
    lambda line : re.sub(
      r"^#define PHP_PROTOBUF_VERSION .*$",
      "#define PHP_PROTOBUF_VERSION \"%s\"" % GetFullVersion(rc_suffix = 'RC'),
      line))

def UpdatePython():
  RewriteTextFile('python/google/protobuf/__init__.py',
    lambda line : re.sub(
      r"^__version__ = '.*'$",
      "__version__ = '%s'" % GetFullVersion(rc_suffix = 'rc'),
      line))

def UpdateRuby():
  RewriteXml('ruby/pom.xml',
             lambda document : ReplaceText(
                 Find(document.documentElement, 'version'), GetFullVersion()))
  RewriteXml('ruby/pom.xml',
             lambda document : ReplaceText(
                 Find(Find(Find(document.documentElement, 'dependencies'), 'dependency'), 'version'),
                 GetFullVersion()))
  RewriteTextFile('ruby/google-protobuf.gemspec',
    lambda line : re.sub(
      r'^  s.version     = ".*"$',
      '  s.version     = "%s"' % GetFullVersion(rc_suffix = '.rc.'),
      line))

def UpdateBazel():
  RewriteTextFile('protobuf_version.bzl',
    lambda line : re.sub(
     r"^PROTOBUF_VERSION = '.*'$",
     "PROTOBUF_VERSION = '%s'" % GetFullVersion(),
     line))


UpdateCMake()
UpdateConfigure()
UpdateCsharp()
UpdateCpp()
UpdateJava()
UpdateJavaScript()
UpdateMakefile()
UpdateObjectiveC()
UpdatePhp()
UpdatePython()
UpdateRuby()
UpdateBazel()
