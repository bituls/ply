import contextlib
import fnmatch
import os
import re
import subprocess


RE_PATCH_IDENTIFIER = re.compile('Ply-Patch: (.*)')


@contextlib.contextmanager
def usedir(path):
    orig_path = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(orig_path)


def get_patch_annotation(commit_msg):
    """Return the Ply-Patch annotation if present in the commit msg.

    Returns None if not present.
    """
    matches = re.search(RE_PATCH_IDENTIFIER, commit_msg)
    if not matches:
        return None

    return matches.group(1)


def recursive_glob(path, glob):
    """Glob against a directory recursively.

    Modified from: http://stackoverflow.com/questions/2186525/
        use-a-glob-to-find-files-recursively-in-python
    """
    matches = []
    for root, dirnames, filenames in os.walk(path):
        for filename in fnmatch.filter(filenames, glob):
            matches.append(os.path.join(root, filename))
    return matches


def path_exists_case_sensitive(path):
    """Determine whether a path exists in a case-sensitive manner.

    This used since Mac's HFS+ filesystem, by default, is case-insensitive.
    """
    basename = os.path.basename(path)
    dirname = os.path.dirname(path)
    return basename in os.listdir(dirname)


def meaningful_diff(source_path, dest_path, diff_output=None):
    """Determines whether a patch changed in a 'meaningful' way.

    The purpose here is to avoid chatty-diffs generated by `ply save` where
    the only changes to a patch-file are around context and index hash
    changes.

    `diff_output` is used for testing and makes `source_path` and `dest_path`
    non-applicable fields.
    """
    if diff_output is None:
        proc = subprocess.Popen(['diff', '-U', '0', source_path, dest_path],
                                stdout=subprocess.PIPE)
        diff_output = proc.communicate()[0]

        if proc.returncode == 0:
            return False
        elif proc.returncode != 1:
            raise Exception('Unknown returncode from diff: %s'
                            % proc.returncode)

    last_index_perms = None
    lines = diff_output.split('\n')

    for line in lines:
        line = line.strip()

        if not line:
            continue
        elif line.startswith('@@'):
            pass
        elif line.startswith('-@@') or line.startswith('+@@'):
            pass
        elif line.startswith('---') or line.startswith('+++'):
            pass
        elif line.startswith('-index'):
            last_index_perms = line.split()[-1]
        elif line.startswith('+index'):
            assert last_index_perms is not None
            perms = line.split()[-1]
            if perms == last_index_perms:
                last_index_perms = None
            else:
                return True
        else:
            # Ensure all -index lines have matching +index lines
            assert last_index_perms is None
            return True

    return False
