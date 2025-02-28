import pytest
import configobj

from dvc.main import main
from dvc.config import Config, ConfigError
from tests.basic_env import TestDvc


class TestConfigCLI(TestDvc):
    def _contains(self, section, field, value, local=False):
        fname = self.dvc.config.files["local" if local else "repo"]

        config = configobj.ConfigObj(fname)
        if section not in config.keys():
            return False

        if field not in config[section].keys():
            return False

        if config[section][field] != value:
            return False

        return True

    def test_root(self):
        ret = main(["root"])
        self.assertEqual(ret, 0)

        # NOTE: check that `dvc root` is not blocked with dvc lock
        with self.dvc.lock:
            ret = main(["root"])
        self.assertEqual(ret, 0)

    def _do_test(self, local=False):
        section = "core"
        field = "analytics"
        section_field = "{}.{}".format(section, field)
        value = "True"
        newvalue = "False"

        base = ["config"]
        if local:
            base.append("--local")

        ret = main(base + [section_field, value])
        self.assertEqual(ret, 0)
        self.assertTrue(self._contains(section, field, value, local))

        ret = main(base + [section_field])
        self.assertEqual(ret, 0)

        ret = main(base + [section_field, newvalue])
        self.assertEqual(ret, 0)
        self.assertTrue(self._contains(section, field, newvalue, local))
        self.assertFalse(self._contains(section, field, value, local))

        ret = main(base + [section_field, "--unset"])
        self.assertEqual(ret, 0)
        self.assertFalse(self._contains(section, field, value, local))

    def test(self):
        self._do_test(False)

    def test_local(self):
        self._do_test(True)

    def test_non_existing(self):
        ret = main(["config", "non_existing_section.field"])
        self.assertEqual(ret, 251)

        ret = main(["config", "global.non_existing_field"])
        self.assertEqual(ret, 251)

        ret = main(["config", "non_existing_section.field", "-u"])
        self.assertEqual(ret, 251)

        ret = main(["config", "global.non_existing_field", "-u"])
        self.assertEqual(ret, 251)

        ret = main(["config", "core.remote", "myremote"])
        self.assertEqual(ret, 0)

        ret = main(["config", "core.non_existing_field", "-u"])
        self.assertEqual(ret, 251)


def test_set_invalid_key(dvc):
    with pytest.raises(ConfigError, match=r"extra keys not allowed"):
        with dvc.config.edit() as conf:
            conf["core"]["invalid_key"] = "value"


def test_merging_two_levels(dvc):
    with dvc.config.edit() as conf:
        conf["remote"]["test"] = {"url": "ssh://example.com"}

    with dvc.config.edit("local") as conf:
        conf["remote"]["test"] = {"password": "1"}

    assert dvc.config["remote"]["test"] == {
        "url": "ssh://example.com",
        "password": "1",
    }


def test_config_loads_without_error_for_non_dvc_repo(tmp_dir):
    # regression testing for https://github.com/iterative/dvc/issues/3328
    Config(validate=True)
