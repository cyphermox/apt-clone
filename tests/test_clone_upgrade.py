#!/usr/bin/python

import apt
import logging
import os
import shutil
import sys
import tarfile
import tempfile
import unittest

from StringIO import StringIO

sys.path.insert(0, "..")
import apt_clone
from apt_clone import AptClone


class TestCloneUpgrade(unittest.TestCase):

    def test_clone_upgrade_regression(self):
        """ regression test against known installs """
        new = self._create_fake_upgradable_root("natty", meta="ubuntu-desktop")
        cache = apt.Cache(rootdir=new)
        clone = AptClone()
        clone._restore_package_selection_in_cache(
            "./data/regression/apt-clone-state-ubuntu.tar.gz", cache)
        self.assertTrue(len(cache.get_changes()) > 0)

    def test_clone_upgrade_synthetic(self):
        """ test clone upgrade with on-the-fly generated chroots """
        for meta in ["ubuntu-standard", "ubuntu-desktop", "kubuntu-desktop", 
                     "xubuntu-desktop"]:
            logging.info("testing %s" % meta)
            old = self._create_fake_upgradable_root("maverick", meta=meta)
            # create statefile based on the old data
            state = tarfile.open("lala.tar.gz", "w:gz")
            state.add(
                os.path.join(old, "var", "lib", "apt-clone", "installed.pkgs"),
                arcname = "./var/lib/apt-clone/installed.pkgs")
            state.close()
            # create new fake environment and try to upgrade
            new = self._create_fake_upgradable_root("natty", meta=meta)
            cache = apt.Cache(rootdir=new)
            clone = AptClone()
            clone._restore_package_selection_in_cache("lala.tar.gz", cache)
            self.assertFalse(cache[meta].marked_delete)
            self.assertTrue(len(cache.get_changes()) > 0)
            # cleanup
            shutil.rmtree(old)
            shutil.rmtree(new)

    def _create_fake_upgradable_root(self, from_dist, 
                                     meta="ubuntu-desktop",
                                     tmpdir=None):
        if tmpdir is None:
            tmpdir = tempfile.mkdtemp()
        sources_list = os.path.join(tmpdir, "etc", "apt", "sources.list")
        if not os.path.exists(os.path.dirname(sources_list)):
            os.makedirs(os.path.dirname(sources_list))
        open(os.path.join(sources_list), "w").write("""
deb http://archive.ubuntu.com/ubuntu %s main restricted universe multiverse
""" % from_dist)
        cache = apt.Cache(rootdir=tmpdir)
        cache.update()
        cache.open()
        if not cache[meta].is_installed:
            cache[meta].mark_install()
            installed_pkgs = os.path.join(tmpdir, "var", "lib", "apt-clone", "installed.pkgs")
            if not os.path.exists(os.path.dirname(installed_pkgs)):
                os.makedirs(os.path.dirname(installed_pkgs))
            dpkg_status = os.path.join(tmpdir, "var", "lib", "dpkg", "status")
            if not os.path.exists(os.path.dirname(dpkg_status)):
                os.makedirs(os.path.dirname(dpkg_status))
            dpkg = open(dpkg_status, "w")
            installed = open(installed_pkgs, "w")
            for pkg in cache:
                if pkg.marked_install:
                    s = str(pkg.candidate.record)
                    s = s.replace("Package: %s\n" % pkg.name,
                                  "Package: %s\n%s\n" % (
                            pkg.name, "Status: install ok installed"))
                    dpkg.write("%s\n" % s)
                    installed.write("%s %s %s\n" % (pkg.name,
                                                    pkg.candidate.version,
                                                    int(pkg.is_auto_installed)))
            dpkg.close()
            installed.close()
        return tmpdir


if __name__ == "__main__":
    unittest.main()