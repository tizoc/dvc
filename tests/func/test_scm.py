import os

from git import Repo

from dvc.scm import Git
from dvc.scm import NoSCM
from dvc.scm import SCM
from dvc.system import System
from dvc.compat import fspath
from tests.basic_env import TestDir
from tests.basic_env import TestGit
from tests.basic_env import TestGitSubmodule
from tests.utils import get_gitignore_content


class TestSCM(TestDir):
    def test_none(self):
        self.assertIsInstance(SCM(self._root_dir), NoSCM)

    def test_git(self):
        Repo.init(os.curdir)
        self.assertIsInstance(SCM(self._root_dir), Git)


class TestSCMGit(TestGit):
    def test_is_repo(self):
        self.assertTrue(Git.is_repo(os.curdir))

    def test_commit(self):
        G = Git(self._root_dir)
        G.add(["foo"])
        G.commit("add")
        self.assertIn("foo", self.git.git.ls_files())

    def test_is_tracked(self):
        foo = os.path.abspath(self.FOO)
        G = Git(self._root_dir)
        G.add([self.FOO, self.UNICODE])
        self.assertTrue(G.is_tracked(foo))
        self.assertTrue(G.is_tracked(self.FOO))
        self.assertTrue(G.is_tracked(self.UNICODE))
        G.commit("add")
        self.assertTrue(G.is_tracked(foo))
        self.assertTrue(G.is_tracked(self.FOO))
        G.repo.index.remove([self.FOO], working_tree=True)
        self.assertFalse(G.is_tracked(foo))
        self.assertFalse(G.is_tracked(self.FOO))
        self.assertFalse(G.is_tracked("not-existing-file"))


class TestSCMGitSubmodule(TestGitSubmodule):
    def test_git_submodule(self):
        self.assertIsInstance(SCM(os.curdir), Git)

    def test_is_submodule(self):
        self.assertTrue(Git.is_submodule(os.curdir))

    def test_commit_in_submodule(self):
        G = Git(self._root_dir)
        G.add(["foo"])
        G.commit("add")
        self.assertTrue("foo" in self.git.git.ls_files())


def _count_gitignore_entries(line):
    lines = get_gitignore_content()
    return lines.count(line)


def test_ignore(tmp_dir, scm):
    foo = fspath(tmp_dir / "foo")
    target = "/foo"

    scm.ignore(foo)
    assert (tmp_dir / ".gitignore").is_file()
    assert _count_gitignore_entries(target) == 1

    scm.ignore(foo)
    assert (tmp_dir / ".gitignore").is_file()
    assert _count_gitignore_entries(target) == 1

    scm.ignore_remove(foo)
    assert _count_gitignore_entries(target) == 0


def test_ignored(tmp_dir, scm):
    tmp_dir.gen({"dir1": {"file1.jpg": "cont", "file2.txt": "cont"}})
    tmp_dir.gen({".gitignore": "dir1/*.jpg"})

    assert scm._ignored(fspath(tmp_dir / "dir1" / "file1.jpg"))
    assert not scm._ignored(fspath(tmp_dir / "dir1" / "file2.txt"))


def test_get_gitignore(tmp_dir, scm):
    tmp_dir.gen({"file1": "contents", "dir": {}})

    data_dir = fspath(tmp_dir / "file1")
    entry, gitignore = scm._get_gitignore(data_dir)
    assert entry == "/file1"
    assert gitignore == fspath(tmp_dir / ".gitignore")

    data_dir = fspath(tmp_dir / "dir")
    entry, gitignore = scm._get_gitignore(data_dir)

    assert entry == "/dir"
    assert gitignore == fspath(tmp_dir / ".gitignore")


def test_get_gitignore_symlink(tmp_dir, scm):
    tmp_dir.gen({"dir": {"subdir": {"data": "contents"}}})
    link = fspath(tmp_dir / "link")
    target = fspath(tmp_dir / "dir" / "subdir" / "data")
    System.symlink(target, link)
    entry, gitignore = scm._get_gitignore(link)
    assert entry == "/link"
    assert gitignore == fspath(tmp_dir / ".gitignore")


def test_get_gitignore_subdir(tmp_dir, scm):
    tmp_dir.gen({"dir1": {"file1": "cont", "dir2": {}}})

    data_dir = fspath(tmp_dir / "dir1" / "file1")
    entry, gitignore = scm._get_gitignore(data_dir)
    assert entry == "/file1"
    assert gitignore == fspath(tmp_dir / "dir1" / ".gitignore")

    data_dir = fspath(tmp_dir / "dir1" / "dir2")
    entry, gitignore = scm._get_gitignore(data_dir)
    assert entry == "/dir2"
    assert gitignore == fspath(tmp_dir / "dir1" / ".gitignore")


def test_gitignore_should_end_with_newline(tmp_dir, scm):
    tmp_dir.gen({"foo": "foo", "bar": "bar"})

    foo = fspath(tmp_dir / "foo")
    bar = fspath(tmp_dir / "bar")
    gitignore = tmp_dir / ".gitignore"

    scm.ignore(foo)
    assert gitignore.read_text().endswith("\n")

    scm.ignore(bar)
    assert gitignore.read_text().endswith("\n")


def test_gitignore_should_append_newline_to_gitignore(tmp_dir, scm):
    tmp_dir.gen({"foo": "foo", "bar": "bar"})

    bar_path = fspath(tmp_dir / "bar")
    gitignore = tmp_dir / ".gitignore"

    gitignore.write_text("/foo")
    assert not gitignore.read_text().endswith("\n")

    scm.ignore(bar_path)
    contents = gitignore.read_text()
    assert gitignore.read_text().endswith("\n")

    assert contents.splitlines() == ["/foo", "/bar"]
